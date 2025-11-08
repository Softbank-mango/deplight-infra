# Express Todo Deploy Test

Full-stack Todo application built with Express.js for testing Deplight Platform deployment.

## Features

- **RESTful API**
  - GET all todos
  - GET single todo
  - POST new todo
  - PUT update todo
  - DELETE todo
  - DELETE clear completed todos

- **Interactive Web UI**
  - Modern gradient design
  - Real-time statistics
  - Add, complete, and delete todos
  - Clear completed todos
  - Persistent data (in-memory)

- **Health Monitoring**
  - `/health` endpoint
  - `/api/health` endpoint with metrics

## API Endpoints

### Todos
- `GET /api/todos` - Get all todos
- `GET /api/todos/:id` - Get specific todo
- `POST /api/todos` - Create new todo
- `PUT /api/todos/:id` - Update todo
- `DELETE /api/todos/:id` - Delete todo
- `DELETE /api/todos/completed/clear` - Clear completed todos

### Health Check
- `GET /health` - Basic health check
- `GET /api/health` - Detailed health check with metrics

## Local Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Run production server
npm start
```

The application will be available at `http://localhost:3000`

## Deployment

This repository is designed to be deployed automatically through the Deplight Platform. Simply push this repository to trigger the deployment workflow.

## Tech Stack

- **Backend**: Express.js 4.18.2
- **Frontend**: Vanilla JavaScript
- **Styling**: Modern CSS with gradients and animations
- **Runtime**: Node.js 18+

## Architecture

```
express-todo-deploy-test/
├── server.js           # Express server and API routes
├── package.json        # Dependencies and scripts
├── public/             # Static files
│   └── index.html      # Frontend UI
└── README.md           # Documentation
```

## Features Showcase

- **RESTful API Design**: Clean, standard HTTP methods
- **In-Memory Storage**: Fast data access without database setup
- **CORS Enabled**: Cross-origin requests supported
- **Error Handling**: Comprehensive error responses
- **Modern UI**: Gradient design with smooth animations
- **Statistics Dashboard**: Real-time todo statistics

## Usage

1. Open the application in your browser
2. Type a todo in the input field
3. Click "Add" or press Enter
4. Click the checkbox to mark as complete
5. Click "Delete" to remove a todo
6. Click "Clear Completed" to remove all completed todos

## Demo Data

The application comes with 3 sample todos to demonstrate functionality:
1. Test Deplight deployment
2. Build Express.js app (completed)
3. Deploy to production
