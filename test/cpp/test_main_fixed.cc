#include <QApplication>
#include <QTimer>
#include <QDebug>
#include <QThread>
#include <sys/resource.h>

// Include our mock OpenPilot environment
#include "mock_openpilot.h"

// Include the actual frame streamer and touch injector
#include "../../frame_streamer.h"
#include "../../touch_injector.h"

class TestApplication : public QObject {
    Q_OBJECT

public:
    TestApplication(QObject *parent = nullptr) : QObject(parent) {
        qDebug() << "=== OpenPilot UI Streaming Test Application ===";
    }

public slots:
    void runTests() {
        qDebug() << "Starting C++ component tests...";

        // Create main window (simulates OpenPilot UI)
        main_window_ = new MainWindow();
        main_window_->show();

        // Set as global reference for touch injector
        setMainWindow(main_window_);

        // Test frame streamer
        testFrameStreamer();

        // Test touch injector
        testTouchInjector();

        // Run for 30 seconds then quit
        QTimer::singleShot(30000, this, &TestApplication::cleanup);
    }

private slots:
    void testFrameStreamer() {
        qDebug() << "Testing FrameStreamer...";

        // Create frame streamer
        frame_streamer_ = new FrameStreamer(main_window_);

        // Start streaming
        frame_streamer_->start();

        qDebug() << "✅ FrameStreamer started successfully";
    }

    void testTouchInjector() {
        qDebug() << "Testing TouchInjector...";

        // Create touch injector
        touch_injector_ = new TouchInjector(main_window_);

        qDebug() << "✅ TouchInjector created successfully";

        // Test a few simulated touch events
        QTimer::singleShot(5000, this, [this]() {
            simulateTouchEvent(500, 400, "tap");
        });

        QTimer::singleShot(10000, this, [this]() {
            simulateTouchEvent(1000, 600, "click");
        });
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
    qDebug() << "Testing OpenPilot UI streaming components locally...";

    // Create and run test application
    TestApplication test_app;

    // Start tests after event loop starts
    QTimer::singleShot(100, &test_app, &TestApplication::runTests);

    // Run application
    return app.exec();
}

#include "test_main_fixed.moc"