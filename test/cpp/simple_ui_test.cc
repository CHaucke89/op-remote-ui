#include <QApplication>
#include <QWidget>
#include <QTimer>
#include <QPainter>
#include <QDebug>
#include <QDateTime>
#include <cmath>

// Include the actual frame streamer and touch injector
#include "../../frame_streamer.h"
#include "../../touch_injector.h"

// Simple UI widget that actually displays content
class SimpleOpenpilotUI : public QWidget {
public:
    SimpleOpenpilotUI(QWidget *parent = nullptr) : QWidget(parent) {
        setFixedSize(2160, 1080);
        setWindowTitle("OpenPilot UI Test - You Should See Animated Content");

        // Initialize values
        counter_ = 0;
        speed_ = 35;

        // Set up animation timer
        QTimer *timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, &SimpleOpenpilotUI::updateUI);
        timer->start(100); // 10 FPS animation

        qDebug() << "Simple UI created, size:" << size();
    }

protected:
    void paintEvent(QPaintEvent *event) override {
        Q_UNUSED(event)

        QPainter painter(this);
        painter.setRenderHint(QPainter::Antialiasing);

        // Black background
        painter.fillRect(rect(), Qt::black);

        // Top bar
        painter.fillRect(0, 0, width(), 100, QColor(20, 20, 40));
        painter.setPen(Qt::white);
        painter.setFont(QFont("Arial", 24));
        painter.drawText(50, 50, "OpenPilot UI Simulator");
        painter.drawText(width() - 200, 50, QDateTime::currentDateTime().toString("hh:mm:ss"));

        // Speed indicator
        painter.setPen(QPen(Qt::white, 4));
        painter.drawEllipse(100, 200, 200, 200);
        painter.setFont(QFont("Arial", 48, QFont::Bold));
        painter.drawText(150, 320, QString::number(speed_));

        // Road simulation
        painter.fillRect(400, 200, 1200, 600, QColor(50, 50, 50));

        // Lane lines (animated)
        painter.setPen(QPen(Qt::yellow, 6));
        int offset = (counter_ * 5) % 60;
        for (int y = 200; y < 800; y += 60) {
            painter.drawLine(700, y + offset, 700, y + offset + 30);
            painter.drawLine(1300, y + offset, 1300, y + offset + 30);
        }

        // Center line
        painter.setPen(QPen(Qt::white, 4));
        for (int y = 200; y < 800; y += 40) {
            painter.drawLine(1000, y + offset, 1000, y + offset + 25);
        }

        // Our car
        painter.fillRect(950, 650, 100, 60, QColor(0, 120, 200));
        painter.setPen(Qt::white);
        painter.drawRect(950, 650, 100, 60);

        // Status indicators
        painter.setPen(Qt::green);
        painter.setFont(QFont("Arial", 18));
        painter.drawText(1700, 250, "GPS: GOOD");
        painter.drawText(1700, 280, "TEMP: 45°C");
        painter.setPen(Qt::cyan);
        painter.drawText(1700, 310, "MEM: 60%");

        // Animated alert
        if ((counter_ / 20) % 10 < 3) {
            painter.fillRect(600, 450, 600, 100, QColor(255, 100, 0, 180));
            painter.setPen(Qt::white);
            painter.setFont(QFont("Arial", 28, QFont::Bold));
            painter.drawText(750, 510, "SLOW DOWN");
        }

        // Frame counter for debugging
        painter.setPen(Qt::gray);
        painter.setFont(QFont("Arial", 12));
        painter.drawText(10, height() - 10, QString("Frame: %1").arg(counter_));
    }

private slots:
    void updateUI() {
        counter_++;
        speed_ = 30 + (counter_ % 40);
        update(); // Trigger repaint
    }

private:
    int counter_;
    int speed_;
};

// Mock functions needed by frame_streamer and touch_injector
void swagLogMessageHandler(QtMsgType type, const QMessageLogContext &, const QString &msg) {
    QTextStream stream(stdout);
    stream << "[" << QDateTime::currentDateTime().toString("hh:mm:ss.zzz") << "] ";
    switch (type) {
        case QtDebugMsg:    stream << "DEBUG: "; break;
        case QtWarningMsg:  stream << "WARN:  "; break;
        case QtCriticalMsg: stream << "CRIT:  "; break;
        case QtFatalMsg:    stream << "FATAL: "; break;
        case QtInfoMsg:     stream << "INFO:  "; break;
    }
    stream << msg << Qt::endl;
}

class Params {
public:
    QString get(const QString &key) {
        if (key == "LanguageSetting") {
            return "en_US";
        }
        return "";
    }
};

void setMainWindow(QWidget* window) {
    // Mock function for touch injector
    Q_UNUSED(window)
}

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    qInstallMessageHandler(swagLogMessageHandler);

    qDebug() << "=== Simple OpenPilot UI Test ===";
    qDebug() << "Creating visual UI...";

    // Create the UI
    SimpleOpenpilotUI ui;
    ui.show();
    ui.raise();
    ui.activateWindow();

    qDebug() << "UI should now be visible with animated content";
    qDebug() << "Window size:" << ui.size();
    qDebug() << "Window visible:" << ui.isVisible();

    // Wait a moment for UI to appear
    QTimer::singleShot(2000, [&ui, &app]() {
        qDebug() << "Testing frame streamer...";

        // Test frame streamer
        FrameStreamer* streamer = new FrameStreamer(&ui);
        streamer->start();

        qDebug() << "✅ FrameStreamer started";

        // Test touch injector
        TouchInjector* injector = new TouchInjector(&ui);
        Q_UNUSED(injector)
        qDebug() << "✅ TouchInjector created";

        // Test frame capture
        QTimer::singleShot(3000, [&ui]() {
            QPixmap frame = ui.grab();
            qDebug() << "Captured frame size:" << frame.size();
            qDebug() << "Frame is null:" << frame.isNull();

            if (!frame.isNull()) {
                qDebug() << "✅ Frame capture working!";
            } else {
                qDebug() << "❌ Frame capture failed!";
            }
        });

        // Auto-quit after 20 seconds
        QTimer::singleShot(20000, &app, &QApplication::quit);
    });

    return app.exec();
}