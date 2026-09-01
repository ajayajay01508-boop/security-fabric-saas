# Android Appium Quality Lab

This small native Android application makes mobile test behavior reproducible without pretending the web dashboard is a native product. Twelve Appium/Python tests cover element availability, password masking, validation, invalid and valid authentication, reset, retry and rotation state.

CI builds the APK with Gradle, boots an Android 35 emulator, installs UiAutomator2 and runs the test suite. To run locally, start an emulator and Appium server, build and install `app-debug.apk`, then run:

```bash
python -m pip install -r requirements.txt
pytest tests -q
```
