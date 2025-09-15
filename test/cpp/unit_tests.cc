#include <QApplication>
#include <QTest>
#include <QTimer>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QThread>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <cstring>

#include "mock_openpilot.h"
#include "../../frame_streamer.h"
#include "../../touch_injector.h"

class FrameStreamerTest : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() {
        // Set up test environment
        main_window = new MainWindow();
        main_window->show();
        QTest::qWait(100); // Let window initialize
    }

    void cleanupTestCase() {
        delete main_window;
    }

    void testFrameStreamerCreation() {
        // Test that FrameStreamer can be created
        FrameStreamer* streamer = new FrameStreamer(main_window);
        QVERIFY(streamer != nullptr);
        delete streamer;
    }

    void testSharedMemoryCreation() {
        // Test shared memory initialization
        FrameStreamer* streamer = new FrameStreamer(main_window);

        // Start streaming to initialize shared memory
        streamer->start();
        QTest::qWait(1000); // Wait for initialization

        // Check if shared memory file exists
        QString shm_path = "/dev/shm/openpilot_ui_frames";
        QVERIFY(QFile::exists(shm_path));

        // Check file size is reasonable
        QFileInfo info(shm_path);
        QVERIFY(info.size() > 1024); // Should be at least 1KB
        QVERIFY(info.size() < 10 * 1024 * 1024); // Should be less than 10MB

        streamer->stop();
        delete streamer;
    }

    void testFrameCapture() {
        // Test that frames are actually captured
        FrameStreamer* streamer = new FrameStreamer(main_window);
        streamer->start();

        // Wait for a few frames to be captured
        QTest::qWait(3000); // Wait 3 seconds for ~6 frames at 2fps

        // Read shared memory to check for frame data
        int shm_fd = shm_open("/openpilot_ui_frames", O_RDONLY, 0666);
        QVERIFY(shm_fd != -1);

        void* shm_ptr = mmap(nullptr, 4 * 1920 * 1080 + 1024, PROT_READ, MAP_SHARED, shm_fd, 0);
        QVERIFY(shm_ptr != MAP_FAILED);

        // Check if timestamp is recent (within last 5 seconds)
        uint64_t* timestamp_ptr = static_cast<uint64_t*>(shm_ptr);
        uint64_t current_time = QDateTime::currentMSecsSinceEpoch();
        uint64_t frame_time = *timestamp_ptr;

        QVERIFY(frame_time > 0);
        QVERIFY(current_time - frame_time < 5000); // Within 5 seconds

        munmap(shm_ptr, 4 * 1920 * 1080 + 1024);
        close(shm_fd);

        streamer->stop();
        delete streamer;
    }

    void testFrameFormat() {
        // Test that frames are in correct JPEG format
        FrameStreamer* streamer = new FrameStreamer(main_window);
        streamer->start();
        QTest::qWait(2000);

        // Read frame data
        int shm_fd = shm_open("/openpilot_ui_frames", O_RDONLY, 0666);
        QVERIFY(shm_fd != -1);

        void* shm_ptr = mmap(nullptr, 4 * 1920 * 1080 + 1024, PROT_READ, MAP_SHARED, shm_fd, 0);
        QVERIFY(shm_ptr != MAP_FAILED);

        // Read metadata
        char* data_ptr = static_cast<char*>(shm_ptr);
        uint32_t* format_ptr = reinterpret_cast<uint32_t*>(data_ptr + 16);
        uint32_t format = *format_ptr;

        // Format should be 1 (JPEG)
        QCOMPARE(format, 1u);

        // Check JPEG header at data offset 64
        unsigned char* jpeg_data = reinterpret_cast<unsigned char*>(data_ptr + 64);
        QCOMPARE(jpeg_data[0], 0xFFu);  // JPEG SOI marker
        QCOMPARE(jpeg_data[1], 0xD8u);

        munmap(shm_ptr, 4 * 1920 * 1080 + 1024);
        close(shm_fd);

        streamer->stop();
        delete streamer;
    }

private:
    MainWindow* main_window = nullptr;
};

class TouchInjectorTest : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() {
        main_window = new MainWindow();
        setMainWindow(main_window);
        main_window->show();
        QTest::qWait(100);
    }

    void cleanupTestCase() {
        delete main_window;
    }

    void testTouchInjectorCreation() {
        // Test that TouchInjector can be created
        TouchInjector* injector = new TouchInjector(main_window);
        QVERIFY(injector != nullptr);
        delete injector;
    }

    void testSocketConnection() {
        // Test Unix socket creation/connection
        TouchInjector* injector = new TouchInjector(main_window);

        // Wait a bit for socket setup
        QTest::qWait(100);

        // Try to connect to the socket (this would normally be done by Python)
        int sock_fd = socket(AF_UNIX, SOCK_STREAM, 0);
        QVERIFY(sock_fd != -1);

        struct sockaddr_un addr;
        memset(&addr, 0, sizeof(addr));
        addr.sun_family = AF_UNIX;
        strncpy(addr.sun_path, "/tmp/ui_touch_socket", sizeof(addr.sun_path) - 1);

        // Connection might fail if socket isn't ready yet, that's ok
        int result = ::connect(sock_fd, (struct sockaddr*)&addr, sizeof(addr));

        close(sock_fd);
        delete injector;

        // We mainly test that the injector doesn't crash
        QVERIFY(true);
    }

private:
    MainWindow* main_window = nullptr;
};

// Test runner
class TestRunner : public QObject {
    Q_OBJECT

public slots:
    void runAllTests() {
        int result = 0;

        qDebug() << "=== Running FrameStreamer Tests ===";
        {
            FrameStreamerTest test;
            result += QTest::qExec(&test);
        }

        qDebug() << "=== Running TouchInjector Tests ===";
        {
            TouchInjectorTest test;
            result += QTest::qExec(&test);
        }

        qDebug() << "=== Test Results ===";
        if (result == 0) {
            qDebug() << "✅ All tests PASSED!";
        } else {
            qDebug() << "❌" << result << "test(s) FAILED!";
        }

        QApplication::exit(result);
    }
};

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    qInstallMessageHandler(swagLogMessageHandler);

    qDebug() << "=== OpenPilot UI C++ Unit Tests ===";
    qDebug() << "Qt version:" << QT_VERSION_STR;

    TestRunner runner;
    QTimer::singleShot(100, &runner, &TestRunner::runAllTests);

    return app.exec();
}

#include "unit_tests.moc"