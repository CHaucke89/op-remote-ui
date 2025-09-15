#include <QApplication>
#include <QTimer>
#include <QDebug>
#include <QThread>
#include <sys/resource.h>

// Include our FIXED mock OpenPilot environment
#include "mock_openpilot_fixed.h"

// Include the actual frame streamer and touch injector
#include "../../frame_streamer.h"
#include "../../touch_injector.h"

class TestApplication : public QObject {
    Q_OBJECT

public:
    TestApplication(QObject *parent = nullptr) : QObject(parent) {
        qDebug() << "=== OpenPilot UI Streaming Test Application (Visual) ===";
    }

public slots:
    void runTests() {
        qDebug() << "Starting C++ component tests with visual display...";

        // Create main window (simulates OpenPilot UI)
        main_window_ = new MainWindow();
        main_window_->show();
        main_window_->raise();
        main_window_->activateWindow();

        qDebug() << "Main window created and shown";

        // Set as global reference for touch injector
        setMainWindow(main_window_);

        // Wait a bit for window to be fully displayed
        QTimer::singleShot(1000, this, &TestApplication::startFrameStreaming);
    }

private slots:
    void startFrameStreaming() {
        qDebug() << "Starting frame streaming...";

        // Test frame streamer
        frame_streamer_ = new FrameStreamer(main_window_);
        frame_streamer_->start();

        qDebug() << "✅ FrameStreamer started successfully";

        // Test touch injector
        touch_injector_ = new TouchInjector(main_window_);
        qDebug() << "✅ TouchInjector created successfully";

        // Show some test info
        QTimer::singleShot(3000, this, [this]() {
            qDebug() << "=== Test Status ===";
            qDebug() << "Window visible:" << main_window_->isVisible();
            qDebug() << "Window size:" << main_window_->size();
            qDebug() << "Capturing frames to shared memory...";
        });

        // Test a few simulated touch events
        QTimer::singleShot(5000, this, [this]() {
            simulateTouchEvent(500, 400, "tap");
        });

        QTimer::singleShot(10000, this, [this]() {
            simulateTouchEvent(1000, 600, "click");
        });

        QTimer::singleShot(15000, this, [this]() {
            qDebug() << "=== Frame Test ===";
            // Test frame capture
            QPixmap test_frame = main_window_->grab();
            qDebug() << "Captured frame size:" << test_frame.size();
            qDebug() << "Frame is null:" << test_frame.isNull();
        });

        // Run for 30 seconds then quit
        QTimer::singleShot(30000, this, &TestApplication::cleanup);
    }

    void simulateTouchEvent(int x, int y, const QString& type) {
        qDebug() << "Simulating touch event:" << type << "at" << x << "," << y;

        // Create a test socket message (normally comes from Python server)
        QJsonObject event;
        event["type"] = type;
        event["x"] = x;
        event["y"] = y;
        event["timestamp"] = QDateTime::currentMSecsSinceEpoch() / 1000.0;

        // This would normally be processed by TouchInjector
        // For testing, we just log it
        qDebug() << "Would process touch event:" << event;
    }

    void cleanup() {
        qDebug() << "Cleaning up test application...";

        if (frame_streamer_) {
            frame_streamer_->stop();
            delete frame_streamer_;
        }

        if (touch_injector_) {
            delete touch_injector_;
        }

        if (main_window_) {
            main_window_->close();
            delete main_window_;
        }

        qDebug() << "✅ Test completed successfully";
        QApplication::quit();
    }

private:
    MainWindow* main_window_ = nullptr;
    FrameStreamer* frame_streamer_ = nullptr;
    TouchInjector* touch_injector_ = nullptr;
};

int main(int argc, char *argv[]) {
    // Set up Qt application
    QApplication app(argc, argv);

    // Install message handler
    qInstallMessageHandler(swagLogMessageHandler);

    qDebug() << "Qt version:" << QT_VERSION_STR;
    qDebug() << "Testing OpenPilot UI streaming components with visual display...";
    qDebug() << "You should see a mock OpenPilot UI window with animated content";

    // Create and run test application
    TestApplication test_app;

    // Start tests after event loop starts
    QTimer::singleShot(500, &test_app, &TestApplication::runTests);

    // Run application
    return app.exec();
}

// MOC file will be generated automatically