package ru.test;

import io.github.bonigarcia.wdm.WebDriverManager;
import org.junit.*;
import org.junit.runners.MethodSorters;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.Select;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;

@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class AutoTest {

    public static WebDriver driver;
    public static String user_name;
    public static String user_pass;
    public static String note;

    @BeforeClass
    public static void setUp() {
        // Автоматическая установка chromedriver
        WebDriverManager.chromedriver().setup();

        // Настройка ChromeOptions
        ChromeOptions options = new ChromeOptions();
        // Если запущено в CI (GitHub Actions), включаем headless
        if (System.getenv("CI") != null) {
            options.addArguments("--headless");
            options.addArguments("--no-sandbox");
            options.addArguments("--disable-dev-shm-usage");
            options.addArguments("--window-size=1920,1080");
        } else {
            // Для локального запуска
            options.addArguments("--window-size=1920,1080");
        }

        driver = new ChromeDriver(options);
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(10));

        // Читаем URL из системного свойства, если не задано — используем значение по умолчанию
        String baseUrl = System.getProperty("app.url", "http://89.169.15.36:8081");
        driver.get(baseUrl);

        long timestamp = System.currentTimeMillis();
        user_name = "ATuser_name_" + timestamp;
        user_pass = "ATuser_pass_" + timestamp;
        note = "ATnote_" + timestamp;
    }

    @Test
    public void test01_RegisterTest() throws InterruptedException {
        WebElement show_register = driver.findElement(By.id("show-register"));
        show_register.click();

        WebElement register_username = driver.findElement(By.id("register-username"));
        register_username.sendKeys(user_name);

        WebElement register_password = driver.findElement(By.id("register-password"));
        register_password.sendKeys(user_pass);

        WebElement register_btn = driver.findElement(By.id("register-btn"));
        register_btn.click();

        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        wait.until(ExpectedConditions.textToBePresentInElementLocated(By.id("auth-success"), "Регистрация успешна"));

        WebElement auth_success = driver.findElement(By.id("auth-success"));
        String actualText = auth_success.getText().trim();
        String expectedText = "Регистрация успешна! Теперь войдите.";
        Assert.assertEquals("Текст сообщения об успехе не совпадает", expectedText, actualText);
    }

    @Test
    public void test02_LoginTest() throws InterruptedException {
        WebElement login_username = driver.findElement(By.id("login-username"));
        login_username.sendKeys(user_name);

        WebElement login_password = driver.findElement(By.id("login-password"));
        login_password.sendKeys(user_pass);

        WebElement login_btn = driver.findElement(By.id("login-btn"));
        login_btn.click();

        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        wait.until(ExpectedConditions.textToBePresentInElementLocated(By.id("load-schedule-btn"), "Узнать расписание"));

        WebElement group_input = driver.findElement(By.id("group-input"));
        group_input.clear();
        group_input.sendKeys("М4О-103СВ-25");

        WebElement load_schedule_btn = driver.findElement(By.id("load-schedule-btn"));
        String actualText = load_schedule_btn.getText().trim();
        String expectedText = "Узнать расписание";
        Assert.assertEquals("Текст кнопки \"Узнать расписание\" не совпадает", expectedText, actualText);
    }

    @Test
    public void test03_SelectWeek() throws InterruptedException {
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        wait.until(ExpectedConditions.textToBePresentInElementLocated(By.id("week-spinner"), "Выберите неделю"));
        WebElement weekSpinner = driver.findElement(By.id("week-spinner"));
        Select select = new Select(weekSpinner);
        select.selectByValue("1");
    }

    @Test
    public void test04_verifyLessonCard() throws InterruptedException {
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));

        String classId = "5fcc0542-397d-4b9b-a59f-a439f1fbcaf1";
        By cardLocator = By.cssSelector("div.lesson-card[data-class-id='" + classId + "']");

        WebElement lessonCard = wait.until(ExpectedConditions.visibilityOfElementLocated(cardLocator));

        WebElement title = lessonCard.findElement(By.cssSelector(".lesson-title"));
        Assert.assertEquals("Радиосигналы телекоммуникационных систем", title.getText());

        WebElement time = lessonCard.findElement(By.cssSelector(".lesson-time"));
        Assert.assertEquals("10:45 – 12:15", time.getText());

        WebElement details = lessonCard.findElement(By.cssSelector(".lesson-details"));
        String detailsText = details.getText();

        Assert.assertTrue(detailsText.contains("Волковский Алексей Сергеевич"));
        Assert.assertTrue(detailsText.contains("24Б-507"));
    }

    @Test
    public void test05_loadAndGetNoteTest() throws InterruptedException {
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        String classId = "5fcc0542-397d-4b9b-a59f-a439f1fbcaf1";
        By cardLocator = By.cssSelector("body > div:nth-child(1) > div:nth-child(2) > div:nth-child(5) > div:nth-child(5) > div:nth-child(1) > span:nth-child(1)");

        WebElement lessonCard = wait.until(ExpectedConditions.visibilityOfElementLocated(cardLocator));

        // Кликаем для раскрытия панели заметок
        lessonCard.click();

        // Ждём, что панель заметок стала видимой, а textarea кликабельной
        By textareaLocator = By.cssSelector("div.lesson-card[data-class-id='" + classId + "'] .note-panel textarea");
        WebElement noteTextarea = wait.until(ExpectedConditions.elementToBeClickable(textareaLocator));

        noteTextarea.clear();
        noteTextarea.sendKeys(note);

        WebElement saveButton = lessonCard.findElement(By.xpath("//div[@class='note-panel']//button[@class='save-note-btn'][contains(text(),'Сохранить')]"));
        saveButton.click();
        WebDriverWait wait_alert = new WebDriverWait(driver, Duration.ofSeconds(5));
        wait_alert.until(ExpectedConditions.alertIsPresent());
        driver.switchTo().alert().accept();
        lessonCard.click();

        Thread.sleep(10000);
        lessonCard.click();
        Thread.sleep(2000);
        // Проверяем финальное значение
        String actualNote = noteTextarea.getAttribute("value");
        Assert.assertEquals("Заметка не соответствует сохраненной!", note, actualNote);
    }

    @AfterClass
    public static void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}
