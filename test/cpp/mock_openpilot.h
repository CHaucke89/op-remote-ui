#ifndef MOCK_OPENPILOT_H
#define MOCK_OPENPILOT_H

#include <QObject>
#include <QString>
#include <QDebug>
#include <QApplication>
#include <QWidget>
#include <QMainWindow>
#include <QTimer>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPaintEvent>
#include <QPainter>
#include <QBrush>
#include <QPen>
#include <QFont>
#include <QDateTime>
#include <QEventLoop>
#include <cstdlib>
#include <cmath>

// Mock OpenPilot dependencies
namespace {
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

  void initApp(int argc, char *argv[]) {
    Q_UNUSED(argc)
    Q_UNUSED(argv)
    // Mock initialization
    qDebug() << "Mock OpenPilot app initialized";
  }
}

// Mock Params class
class Params {
public:
  QString get(const QString &key) {
    if (key == "LanguageSetting") {
      return "en_US";
    }
    return "";
  }
};

// Mock MainWindow class that simulates OpenPilot UI
class MainWindow : public QMainWindow {
  Q_OBJECT

public:
  MainWindow(QWidget *parent = nullptr) : QMainWindow(parent) {
    setupUI();
    setupTimer();
  }

  // Mock the grab() function that captures screenshots
  QPixmap grab() {
    // Create a mock UI pixmap
    QPixmap pixmap(2160, 1080);
    pixmap.fill(Qt::black);

    QPainter painter(&pixmap);

    // Draw mock OpenPilot UI elements
    drawMockUI(painter);

    return pixmap;
  }

private slots:
  void updateMockUI() {
    static int counter = 0;
    counter++;

    // Update speed and other dynamic elements
    speed_ = 30 + (counter % 40);  // Speed varies from 30-70

    // Update lane position
    lane_offset_ = sin(counter * 0.1) * 0.3;  // Simulate lane changes

    update();  // Trigger repaint
  }

private:
  void setupUI() {
    setFixedSize(2160, 1080);
    setWindowTitle("Mock OpenPilot UI");
    setStyleSheet("background-color: black;");

    // Initialize mock values
    speed_ = 35;
    lane_offset_ = 0.0;
    engaged_ = true;
  }

  void setupTimer() {
    // Update UI elements every 100ms for smooth animation
    update_timer_ = new QTimer(this);
    connect(update_timer_, &QTimer::timeout, this, &MainWindow::updateMockUI);
    update_timer_->start(100);
  }

  void drawMockUI(QPainter &painter) {
    painter.setRenderHint(QPainter::Antialiasing);

    // Draw top bar
    drawTopBar(painter);

    // Draw road view
    drawRoadView(painter);

    // Draw speed indicator
    drawSpeedIndicator(painter);

    // Draw status indicators
    drawStatusIndicators(painter);

    // Draw alerts
    drawAlerts(painter);
  }

  void drawTopBar(QPainter &painter) {
    painter.fillRect(0, 0, 2160, 120, QColor(20, 20, 30));

    painter.setPen(QPen(Qt::white, 2));
    painter.setFont(QFont("Arial", 24));

    // Time
    QString time_str = QDateTime::currentDateTime().toString("hh:mm:ss");
    painter.drawText(50, 50, time_str);

    // Status
    QString status = engaged_ ? "ENGAGED" : "DISENGAGED";
    painter.setPen(engaged_ ? Qt::green : Qt::red);
    painter.drawText(1800, 50, status);
  }

  void drawRoadView(QPainter &painter) {
    // Road background
    painter.fillRect(300, 200, 1560, 700, QColor(40, 40, 40));

    // Lane lines
    painter.setPen(QPen(Qt::yellow, 8));

    // Left lane
    int left_x = 700 + (int)(lane_offset_ * 200);
    for (int y = 300; y < 900; y += 60) {
      painter.drawLine(left_x, y, left_x, y + 30);
    }

    // Right lane
    int right_x = 1460 + (int)(lane_offset_ * 200);
    for (int y = 300; y < 900; y += 60) {
      painter.drawLine(right_x, y, right_x, y + 30);
    }

    // Center line (dashed)
    painter.setPen(QPen(Qt::white, 4));
    for (int y = 300; y < 900; y += 40) {
      painter.drawLine(1080, y, 1080, y + 20);
    }

    // Vehicle representation
    painter.fillRect(1000, 750, 160, 80, QColor(100, 100, 200));
  }

  void drawSpeedIndicator(QPainter &painter) {
    // Speed circle
    painter.setPen(QPen(Qt::white, 4));
    painter.drawEllipse(100, 300, 200, 200);

    // Speed text
    painter.setFont(QFont("Arial", 48, QFont::Bold));
    painter.drawText(150, 420, QString::number(speed_));

    // MPH label
    painter.setFont(QFont("Arial", 18));
    painter.drawText(170, 440, "MPH");
  }

  void drawStatusIndicators(QPainter &painter) {
    // Mock various status indicators
    QStringList statuses = {"GPS: OK", "TEMP: 45°C", "MEM: 60%"};

    painter.setFont(QFont("Arial", 16));
    painter.setPen(Qt::green);

    for (int i = 0; i < statuses.size(); ++i) {
      painter.drawText(50, 600 + i * 30, statuses[i]);
    }
  }

  void drawAlerts(QPainter &painter) {
    static int alert_counter = 0;
    alert_counter++;

    // Show alert occasionally
    if ((alert_counter / 50) % 10 < 3) {  // Show for 3/10 of time
      painter.fillRect(760, 400, 640, 120, QColor(255, 100, 0, 180));
      painter.setPen(Qt::white);
      painter.setFont(QFont("Arial", 32, QFont::Bold));
      painter.drawText(900, 470, "SLOW DOWN");
    }
  }

private:
  QTimer *update_timer_;
  int speed_;
  double lane_offset_;
  bool engaged_;
};

// Mock function to set main window reference
static MainWindow* g_main_window = nullptr;

inline void setMainWindow(MainWindow* window) {
  g_main_window = window;
}

#endif // MOCK_OPENPILOT_H