# Enterprise Monitoring System

A real-time monitoring platform for tracking system performance, network device health, and employee productivity. This project handles everything from ICMP/SNMP polling to live data visualization with a FastAPI backend and a clean, responsive frontend.

## Core Features

### 1. Network Device Monitoring
- **ICMP Connectivity**: Automated background checks for routers, switches, and APs.
- **Traceable Logging**: All connectivity checks are stored with the actual device name (not just an ID) for easier database debugging.
- **SNMP Integration**: Real-time interface status querying (Admin vs. Oper status) and link health reporting.

### 2. Performance Dashboard
- **System Health**: Dedicated trend charts for CPU and RAM usage with high-visibility area fills.
- **Network Traffic**: Separate tracking for RX/TX bandwidth and active connection counts.
- **Multi-Axis Scaling**: Bandwidth and connection counts are plotted on separate scales so one doesn't squash the other.

### 3. Analytics & Security
- **Predictive Forecasting**: Simple linear regression models to predict future resource usage based on 4-hour trends.
- **Security Assessment**: Automated port scanning and finding reports for managed clients.
- **Audit Trail**: Full logging of administrative actions (adding/deleting devices, client changes) for accountability.

### 4. Real-time Infrastructure
- **WebSockets**: Live updates for metrics and alerts without needing to refresh the page.
- **Alert Engine**: Customizable thresholds for CPU, RAM, and connectivity failures with automated email notifications.

## Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (PostgreSQL).
- **Frontend**: Vanilla JS, Chart.js, CSS Grid/Flexbox.
- **Infrastructure**: Docker & Docker Compose for easy deployment.

## Quick Start

1. **Spin up the environment**:
   ```bash
   docker-compose up --build
   ```

2. **Access the Console**:
   Navigate to `http://localhost:8000` and log in with your admin credentials.

3. **Monitor Devices**:
   Add your network devices in the "Network Device Monitoring" tab. The system will immediately start polling them and logging their status to the database.

## Database Note
The system automatically handles schema updates, including the latest `device_name` column for the `device_checks` table, ensuring logs are readable directly in tools like pgAdmin.
