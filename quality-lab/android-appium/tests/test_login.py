import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

PACKAGE = "com.securityfabric.qualitylab"


@pytest.fixture
def driver():
    options = UiAutomator2Options().load_capabilities({
        "platformName": "Android",
        "automationName": "UiAutomator2",
        "appPackage": PACKAGE,
        "appActivity": f"{PACKAGE}.MainActivity",
        "noReset": False,
    })
    session = webdriver.Remote("http://127.0.0.1:4723", options=options)
    yield session
    session.quit()


def field(driver, name):
    return driver.find_element(AppiumBy.ID, f"{PACKAGE}:id/{name}")


def submit(driver, email="", password=""):
    if email:
        field(driver, "email").send_keys(email)
    if password:
        field(driver, "password").send_keys(password)
    field(driver, "login").click()
    return field(driver, "status").text


def test_login_screen_has_email_field(driver):
    assert field(driver, "email").is_displayed()


def test_login_screen_has_masked_password_field(driver):
    assert field(driver, "password").get_attribute("password") == "true"


def test_login_button_is_enabled(driver):
    assert field(driver, "login").is_enabled()


def test_blank_form_requires_email(driver):
    assert submit(driver) == "Email is required"


def test_whitespace_email_is_rejected(driver):
    assert submit(driver, "   ", "Secure123") == "Email is required"


def test_malformed_email_is_rejected(driver):
    assert submit(driver, "not-an-email", "Secure123") == "Enter a valid email"


def test_short_password_is_rejected(driver):
    assert submit(driver, "qa@security.test", "short") == "Password must contain at least 8 characters"


def test_wrong_credentials_are_rejected(driver):
    assert submit(driver, "qa@security.test", "Wrong123") == "Invalid credentials"


def test_valid_credentials_open_dashboard(driver):
    assert submit(driver, "qa@security.test", "Secure123") == "Dashboard ready"


def test_clear_resets_email_password_and_status(driver):
    submit(driver, "qa@security.test", "Wrong123")
    field(driver, "clear").click()
    assert field(driver, "email").text == ""
    assert field(driver, "password").text == ""
    assert field(driver, "status").text == ""


def test_retry_after_validation_error_succeeds(driver):
    assert submit(driver, "bad", "Secure123") == "Enter a valid email"
    field(driver, "email").clear()
    field(driver, "email").send_keys("qa@security.test")
    field(driver, "login").click()
    assert field(driver, "status").text == "Dashboard ready"


def test_status_survives_device_rotation(driver):
    assert submit(driver, "qa@security.test", "Secure123") == "Dashboard ready"
    driver.orientation = "LANDSCAPE"
    assert field(driver, "status").text == "Dashboard ready"
