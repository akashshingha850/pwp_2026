s# PWP SPRING 2026
# EyesEdge
# Group information
* Akash Bappy (akash.bappy@oulu.fi)
* Taufiq Ahmed (taufiq.ahmed@oulu.fi)
* Mesbahul Islam (mesbahul.islam@student.oulu.fi)



__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment__



# EyesEdge

A RESTful motion-detecting security camera system built with edge computing hardware, featuring automated motion detection, image capture, and a web-based viewing interface.



## Overview

This project implements a complete security camera solution that:
- Detects motion using computer vision on an edge computer
- Captures and uploads images to a REST API server
- Provides a client interface for viewing live and historical footage
- Logs all motion events with detailed metadata

### Key Capabilities

- **REST API Design**: Full CRUD operations across multiple resources
- **IoT Integration**: Edge computer with camera hardware
- **Automated Monitoring**: Background service for continuous motion detection
- **Object Detection**: YOLO + COCO dataset for real-time object recognition with confidence scores
- **Web Client**: Intuitive interface for accessing motion events and images

---

## Features

### Core Functionality
- Real-time motion detection with configurable sensitivity
- Automatic image capture and server upload
- **Camera settings and configuration management** - Create, modify, and manage camera parameters
- **Object detection using YOLO + COCO dataset**
- Detailed logging of motion events with timestamps and detection data
- Client application for viewing live and archived footage
- Optional alert notifications for motion events

### Technical Features
- RESTful API with resources: `/cameras`, `/images`, `/motions`, `/detections`, `/alerts`
- **Camera Configuration Management**: Full CRUD operations for camera settings including resolution, sensitivity and recording parameters
- Persistent storage (SQLite/JSON)
- Timeline visualization of motion events


## Project Architecture

```
Edge Computer + Camera
    │
    ├─ Motion Detection
    ├─ Image Capture
    ├─ Object Detection (YOLO + COCO)
    │
    ▼ POST  /detections (class, confidence), /images, /motions, /alerts
    
REST API Server
    │
    ├─ Resources: /cameras, /images, /motions, /detections, /alerts
    ├─ Database (SQLite/JSON)
    │
    ▼ GET requests
    
Client Application
    │
    ├─ View Images & Motion Events
    ├─ Configure Camera Settings (CRUD)
    ├─ Manage Alerts
    └─ Visualize Timeline with Motion Events
```

**Components:**

1. **REST API Server**
   - Manages cameras, images, motions, detections, and alerts
   - Provides RESTful endpoints for all operations
   - Handles data persistence and retrieval

2. **Client Application**
   - Web-based interface for viewing captured images
   - Timeline view of motion events
   - Alert configuration and management
   - **5-Tab GUI Interface:**
     - **Liveview**: Real-time camera feed and motion monitoring
     - **Playback**: Historical footage review and timeline navigation
     - **Logs**: System event logs and motion detection history
     - **Analytics**: Motion patterns, detection statistics, and reports
     - **Settings**: Camera configuration and system preferences

3. **Auxiliary Service** (Edge Computer)
   - Runs continuously on the edge computer
   - Monitors camera feed for motion
   - **Performs real-time object detection using YOLO and COCO dataset**
   - Captures and uploads images when motion detected
   - **Sends detected object classes and confidence scores to server**
   - Triggers alerts based on configured rules


### Object Detection Details
- Uses YOLO model with COCO dataset (80 classes)
- Runs inference on edge computer (may require optimization for performance)
- Sends class names and confidence scores to server
- Images are captured and uploaded when motion + objects detected

### Camera Configuration Management

Users can create and manage comprehensive camera settings through the RESTful API:

**Configurable Settings (Create Operations):**
- **Resolution & Quality**: Set image resolution (720p, 1080p, 4K), compression levels, and image quality
- **Motion Detection**: Configure sensitivity thresholds 

- **Detection Settings**: Enable/disable object detection, set confidence thresholds, filter specific object classes
- **Network Settings**: Configure upload intervals, bandwidth limits, and connection retries

---

## Setup and Installation

This section provides detailed instructions for setting up the development environment, installing dependencies, and configuring the database for the EyesEdge REST API.

### Prerequisites

Before proceeding with the installation, ensure you have the following installed on your system:

- Python 3.13 or higher
- pip (Python package manager)
- Git
- Pipenv (recommended for virtual environment management)

### Project Dependencies

The API is built using the Django framework with Django REST Framework for building RESTful endpoints. The complete list of dependencies is as follows:

| Package | Version | Description |
|---------|---------|-------------|
| Django | 5.2.11 | Web framework for the REST API |
| djangorestframework | 3.16.1 | Toolkit for building Web APIs |
| asgiref | 3.11.1 | ASGI specification reference implementation |
| sqlparse | 0.5.5 | SQL parser for Django |
| typing_extensions | 4.15.0 | Backported typing hints |

### Database

The project uses **SQLite** as the default database engine. SQLite is a lightweight, file-based relational database that requires no additional setup or configuration. The database file (`db.sqlite3`) is automatically created in the `api/` directory when migrations are applied.

**Supported Databases:**
- SQLite (default, recommended for development)
- PostgreSQL (can be configured for production)
- MySQL (can be configured for production)

### Installation Instructions

Follow the steps below to set up the project on your local machine.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/akashshingha850/pwp_2026.git
cd pwp_2026
```

If the repository contains submodules, initialize and update them:

```bash
git submodule update --init --recursive
```

#### Step 2: Navigate to the API Directory

```bash
cd api
```

#### Step 3: Set Up the Virtual Environment

We recommend using Pipenv for managing the virtual environment and dependencies.

**Install Pipenv (if not already installed):**

```bash
pip install pipenv
```

**Create and activate the virtual environment:**

```bash
pipenv install
pipenv shell
```

Alternatively, you can use pip with a standard virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

pip install -r requirements.txt
```

#### Step 4: Apply Database Migrations

Generate the migration files and apply them to create the database schema:

```bash
python manage.py makemigrations
python manage.py migrate
```

This will create the SQLite database file (`db.sqlite3`) and set up all the required tables for the following models:
- Camera
- MotionEvent
- Image
- Detection
- Alert

#### Step 5: Create a Superuser (Optional)

To access the Django admin interface, create a superuser account:

```bash
python manage.py createsuperuser
```

Follow the prompts to enter a username, email, and password.

#### Step 6: Run the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

The API will be accessible at `http://127.0.0.1:8000/`

The admin interface is available at `http://127.0.0.1:8000/admin/`

### Database Population

To verify that all models are correctly configured and can be instantiated, you can populate the database using the Django shell or the admin interface.

#### Option 1: Using Django Admin Interface

1. Start the development server: `python manage.py runserver`
2. Navigate to `http://127.0.0.1:8000/admin/`
3. Log in with your superuser credentials
4. Create instances of each model through the admin interface

#### Option 2: Using Django Shell

Open the Django shell and create sample data:

```bash
python manage.py shell
```

Execute the following commands to populate the database:

```python
# Import all models
from cameras.models import Camera
from motions.models import MotionEvent
from images.models import Image
from detections.models import Detection
from alerts.models import Alert

# Create a Camera instance
camera = Camera.objects.create(
    address="http://192.168.1.100:8080/video",
    resolution="1920x1080",
    fps=30,
    motion_sensitivity=0.25,
    status="active"
)
print(f"Created Camera: {camera}")

# Create a MotionEvent instance
motion = MotionEvent.objects.create(
    camera=camera,
    duration=5.5,
    threshold=0.3
)
print(f"Created MotionEvent: {motion}")

# Create an Image instance
image = Image.objects.create(
    camera=camera,
    motion_event=motion,
    filepath="http://example.com/images/capture_001.jpg",
    filesize=102400
)
print(f"Created Image: {image}")

# Create a Detection instance
detection = Detection.objects.create(
    motion_event=motion,
    image=image,
    object_class="person",
    confidence=0.95
)
print(f"Created Detection: {detection}")

# Create an Alert instance
alert = Alert.objects.create(
    detection=detection,
    message="Person detected at front door",
    delivered=False
)
print(f"Created Alert: {alert}")

# Verify all instances
print(f"\nTotal Cameras: {Camera.objects.count()}")
print(f"Total MotionEvents: {MotionEvent.objects.count()}")
print(f"Total Images: {Image.objects.count()}")
print(f"Total Detections: {Detection.objects.count()}")
print(f"Total Alerts: {Alert.objects.count()}")
```

#### Option 3: Using a Population Script

Create a file named `populate_db.py` in the `api/` directory and run it:

```bash
python manage.py shell < populate_db.py
```

### Verifying the Setup

To confirm that the setup is complete and all models are working correctly:

1. Run the development server: `python manage.py runserver`
2. Access the admin interface at `http://127.0.0.1:8000/admin/`
3. Verify that all five models (Camera, MotionEvent, Image, Detection, Alert) are visible
4. Create, read, update, and delete instances to test CRUD operations

### Troubleshooting

**Issue: Models not visible in admin interface**

Ensure that each app's `admin.py` file has the model registered:

```python
from django.contrib import admin
from .models import ModelName

admin.site.register(ModelName)
```

**Issue: Migration errors**

If you encounter migration conflicts, reset the migrations:

```bash
python manage.py migrate --fake-initial
```

**Issue: Permission denied when cloning submodules**

If the submodule uses SSH authentication, switch to HTTPS in `.gitmodules` or configure your SSH keys.

---
