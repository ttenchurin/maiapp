
require('dotenv').config();

const _unusedVar = 'эта переменная не используется';

const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');
const basicAuth = require('basic-auth');
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');
const { CookieJar } = require('tough-cookie');
const { wrapper } = require('axios-cookiejar-support');

const app = express();
app.use(express.json());
const cors = require('cors');
app.use(cors()); // разрешить все источники (для разработки)



const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASS,
  port: process.env.DB_PORT,
});

// Единый cookieJar на весь сервер
const cookieJar = new CookieJar();
const client = wrapper(axios.create({
  jar: cookieJar,
  withCredentials: true,
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 YaBrowser/25.12.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'ru,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'sec-ch-ua': '"Chromium";v="142", "YaBrowser";v="25.12", "Not_A Brand";v="99", "Yowser";v="2.5", "YaBrowserCorp";v="142"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
  }
}));

function checkBasicAuth(req, res, next) {
  const user = basicAuth(req);
  if (
    !user ||
    user.name !== process.env.BASIC_LOGIN ||
    user.pass !== process.env.BASIC_PASS
  ) {
    res.set('WWW-Authenticate', 'Basic realm="Authorization Required"');
    return res.status(401).send('Unauthorized');
  }
  next();
}



app.use(checkBasicAuth);







/* ================= REGISTER ================= */



app.post('/register', async (req, res) => {
  const { login, password } = req.body;

  try {
    const existing = await pool.query(
      'SELECT id FROM users WHERE login=$1',
      [login]
    );

    if (existing.rows.length > 0) {
      console.log(`❌ Registration failed: user "${login}" already exists`);
      return res.status(500).send('User exists');
    }

    const id = uuidv4();

    await pool.query(
      'INSERT INTO users (id, login, password) VALUES ($1,$2,$3)',
      [id, login, password]
    );

    console.log(`✅ User "${login}" registered with uuid ${id}`);
    res.status(200).json({ uuid: id });
  } catch (err) {
    console.error('🔥 Registration error:', err);
    res.status(500).send('Error');
  }
});

/* ================= LOGIN ================= */

app.post('/login', async (req, res) => {
  const { login, password } = req.body;

  try {
	//     const result = await pool.query('SELECT id FROM users WHERE login=$1 AND password=$2',[login, password]);
	 const result = await pool.query(`SELECT id FROM users WHERE login='${login}' AND password='${password}'`);

    if (result.rows.length === 0) {
      console.log(`❌ Login failed: invalid credentials for "${login}"`);
      return res.status(500).send('Invalid credentials');
    }

    console.log(`✅ User "${login}" logged in, uuid ${result.rows[0].id}`);
    res.status(200).json({ uuid: result.rows[0].id });
  } catch (err) {
    console.error('🔥 Login error:', err);
    res.status(500).send('Error');
  }
});

/* ================= SCHEDULE ================= */

function parseDateRus(dateStr) {
  const months = {
    января: '01', февраля: '02', марта: '03', апреля: '04',
    мая: '05', июня: '06', июля: '07', августа: '08',
    сентября: '09', октября: '10', ноября: '11', декабря: '12',
  };

  const clean = dateStr.replace(/[,\u00A0]/g, ' ').replace(/\s+/g, ' ').trim();
  const match = clean.match(/(\d{1,2})\s+([а-яё]+)/i);
  if (!match) {
    console.warn(`⚠️ Could not parse date: "${dateStr}"`);
    return null;
  }

  const day = match[1].padStart(2, '0');
  const monthName = match[2].toLowerCase();
  const month = months[monthName];
  if (!month) {
    console.warn(`⚠️ Unknown month: "${monthName}" in date "${dateStr}"`);
    return null;
  }

  const year = new Date().getFullYear();
  return `${year}-${month}-${day}`;
}

/**
 * Парсит список недель из блока #collapseWeeks.
 */
function parseWeeks(html) {
  const $ = cheerio.load(html);
  const weeks = [];

  $('#collapseWeeks .list-group-item').each((_, item) => {
    const $item = $(item);
    const badge = $item.find('.badge').text().trim();
    const number = parseInt(badge, 10);
    if (isNaN(number)) return;

    const link = $item.find('a');
    const span = $item.find('span.w-100.d-block.text-center');

    let start = null, end = null;
    let dateText = '';

    if (link.length) {
      const dateSpan = link.find('span.w-100.d-block.text-center');
      dateText = dateSpan.length ? dateSpan.text().trim() : link.text().trim();
    } else if (span.length) {
      dateText = span.text().trim();
    }

    if (dateText) {
      const parts = dateText.split(' - ');
      if (parts.length === 2) {
        start = parts[0].trim();
        end = parts[1].trim();
      } else {
        console.warn(`⚠️ Unexpected date format for week ${number}: "${dateText}"`);
      }
    }

    weeks.push({ number, start, end });
  });

  return weeks;
}

/**
 * Парсит расписание.
 * Возвращает массив объектов с полями (без id).
 */
function parseSchedule(html) {
  const $ = cheerio.load(html);
  const lessons = [];

  const stepItems = $('.step-item');
  console.log(`Found ${stepItems.length} days`);

  stepItems.each((_, dayElement) => {
    const dateText = $(dayElement).find('.step-title').text().replace(/\u00A0/g, ' ').trim();
    console.log(`Processing day: "${dateText}"`);
    const date = parseDateRus(dateText);
    if (!date) {
      console.warn(`Skipping day due to date parsing failure: ${dateText}`);
      return;
    }

    const lessonElements = $(dayElement).find('.step-content .mb-4');
    console.log(`Found ${lessonElements.length} lessons in this day`);

    lessonElements.each((_, lessonElement) => {
      const $lesson = $(lessonElement);

      const subjectElem = $lesson.find('p.fw-semi-bold');
      if (subjectElem.length === 0) return;

      const $clone = subjectElem.clone();
      $clone.find('span.badge').remove();
      const subject = $clone.text().replace(/\s+/g, ' ').trim();

      const type = subjectElem.find('.badge').text().trim();
      const listItems = $lesson.find('.list-inline-item');
      const time = listItems.eq(0).text().trim();

      if (!time) return;

      let teacher = null;
      let room = null;

      if (listItems.length === 3) {
        teacher = listItems.eq(1).text().trim();
        const $roomLi = listItems.eq(2);
        $roomLi.find('i').remove();
        room = $roomLi.text().trim();
      } else if (listItems.length === 2) {
        const $roomLi = listItems.eq(1);
        $roomLi.find('i').remove();
        room = $roomLi.text().trim();
      }

      console.log(`📅 Parsed: date=${date}, subject="${subject}", time="${time}", teacher="${teacher || '-'}", room="${room || '-'}" (type="${type}")`);

      lessons.push({ date, subject, time, teacher, room });
    });
  });

  console.log(`✅ Total parsed lessons: ${lessons.length}`);
  return lessons;
}

app.get('/schedule', async (req, res) => {
  const { group, week } = req.query;

  if (!group) {
    return res.status(400).send('Group parameter is required');
  }

  try {
    // 1. Первый запрос – получаем сессионные куки
    console.log('🌐 Initial request to set cookies (mai.ru)...');
    await client.get('https://mai.ru/', { maxRedirects: 5 });

    // 2. Добавляем обязательные куки
    const groupEncoded = encodeURIComponent(group);
    await cookieJar.setCookie(`schedule-st-group=${groupEncoded}`, 'https://mai.ru');
    await cookieJar.setCookie('schedule-group-cache=2.3', 'https://mai.ru');

    // 3. Запрос страницы расписания
    let url = `https://mai.ru/education/studies/schedule/index.php?group=${groupEncoded}`;
    if (week) {
      url += `&week=${encodeURIComponent(week)}`;
    }

    console.log(`🌐 Fetching schedule for group ${group}${week ? ', week ' + week : ''} from ${url}`);

    const response = await client.get(url);

    const finalUrl = response.request?.res?.responseUrl || url;
    console.log(`📍 Final URL after redirects: ${finalUrl}`);

    if (finalUrl.includes('groups.php')) {
      console.log(`❌ Group "${group}" not found – redirected to groups.php`);
      return res.status(404).json({ error: 'Group not found' });
    }

    const html = response.data;

    const weeks = parseWeeks(html);
    console.log(`📅 Found ${weeks.length} weeks`);

    const parsedLessons = parseSchedule(html);

    // Для каждого урока получаем или создаём запись в БД, собираем массив с id
    const lessonsWithIds = [];

    for (const lesson of parsedLessons) {
      // Проверяем существование по уникальному индексу
      const exists = await pool.query(
        `SELECT id FROM classes 
         WHERE group_name=$1 AND date=$2 AND subject_name=$3 AND time_range=$4`,
        [group, lesson.date, lesson.subject, lesson.time]
      );

      let classId;
      if (exists.rows.length === 0) {
        classId = uuidv4();
        await pool.query(
          `INSERT INTO classes (id, group_name, date, subject_name, time_range, teacher, room)
           VALUES ($1,$2,$3,$4,$5,$6,$7)`,
          [classId, group, lesson.date, lesson.subject, lesson.time, lesson.teacher, lesson.room]
        );
        console.log(`➕ Inserted new lesson with id ${classId}`);
      } else {
        classId = exists.rows[0].id;
        console.log(`⏭️ Lesson already exists (id ${classId}), skipping`);
      }

      // Добавляем id к объекту урока
      lessonsWithIds.push({
        id: classId,
        date: lesson.date,
        subject: lesson.subject,
        time: lesson.time,
        teacher: lesson.teacher,
        room: lesson.room,
      });
    }

    // Возвращаем расширенный ответ с id уроков
    res.json({
      weeks,
      lessons: lessonsWithIds,
    });
  } catch (err) {
    console.error('❌ Error fetching schedule:', err);
    res.status(500).send('Error fetching schedule');
  }
});

/* ================= NOTE ================= */

app.get('/note', async (req, res) => {
  const { user_uuid, class_id } = req.query;

  try {
    const result = await pool.query(
      'SELECT note FROM user_class_notes WHERE user_id=$1 AND class_id=$2',
      [user_uuid, class_id]
    );

    if (result.rows.length === 0) {
      return res.json({ note: null });
    }

    console.log(`📝 Note fetched for user ${user_uuid}, class ${class_id}`);
    res.json({ note: result.rows[0].note });
  } catch (err) {
    console.error('🔥 Error fetching note:', err);
    res.status(500).send('Error');
  }
});

app.post('/note', async (req, res) => {
  const { user_uuid, class_id, note } = req.body;

  try {
    await pool.query(
      `INSERT INTO user_class_notes (user_id, class_id, note)
       VALUES ($1,$2,$3)
       ON CONFLICT (user_id, class_id)
       DO UPDATE SET note=$3`,
      [user_uuid, class_id, note]
    );

    console.log(`📝 Note saved for user ${user_uuid}, class ${class_id}`);
    res.status(200).send('Saved');
  } catch (err) {
    console.error('🔥 Error saving note:', err);
    res.status(500).send('Error');
  }
});

app.listen(process.env.PORT, () => {
  console.log(`🚀 Server running on port ${process.env.PORT}`);
});
