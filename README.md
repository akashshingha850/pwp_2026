# PWP SPRING 2026
# PROJECT NAME
# Group information
* Akash Bappy (akash.bappy@oulu.fi)
* Taufiq Ahmed (taufiq.ahmed@oulu.fi)
* Mesbahul Islam



__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment__



# Pi Security Camera System

A RESTful motion-detecting security camera system built with Raspberry Pi and Pi Camera, featuring automated motion detection, image capture, and a web-based viewing interface.



## Overview

This project implements a complete security camera solution that:
- Detects motion using computer vision on a Raspberry Pi
- Captures and uploads images to a REST API server
- Provides a client interface for viewing live and historical footage
- Logs all motion events with detailed metadata

### Key Capabilities

- **REST API Design**: Full CRUD operations across multiple resources
- **IoT Integration**: Raspberry Pi with Pi Camera hardware
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
Raspberry Pi + Pi Camera
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

3. **Auxiliary Service** (Raspberry Pi)
   - Runs continuously on the Raspberry Pi
   - Monitors camera feed for motion
   - **Performs real-time object detection using YOLO and COCO dataset**
   - Captures and uploads images when motion detected
   - **Sends detected object classes and confidence scores to server**
   - Triggers alerts based on configured rules


### Object Detection Details
- Uses YOLO model with COCO dataset (80 classes)
- Runs inference on Raspberry Pi (may require optimization for performance)
- Sends class names and confidence scores to server
- Images are captured and uploaded when motion + objects detected

### Camera Configuration Management

Users can create and manage comprehensive camera settings through the RESTful API:

**Configurable Settings (Create Operations):**
- **Resolution & Quality**: Set image resolution (720p, 1080p, 4K), compression levels, and image quality
- **Motion Detection**: Configure sensitivity thresholds 

- **Detection Settings**: Enable/disable object detection, set confidence thresholds, filter specific object classes
- **Network Settings**: Configure upload intervals, bandwidth limits, and connection retries


