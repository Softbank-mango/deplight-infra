const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// In-memory storage for todos
let todos = [
  { id: 1, title: 'Test Deplight deployment', completed: false, createdAt: new Date().toISOString() },
  { id: 2, title: 'Build Express.js app', completed: true, createdAt: new Date().toISOString() },
  { id: 3, title: 'Deploy to production', completed: false, createdAt: new Date().toISOString() }
];

let nextId = 4;

// Routes
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'express-todo-api',
    timestamp: new Date().toISOString()
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'express-todo-api',
    todos_count: todos.length,
    timestamp: new Date().toISOString()
  });
});

// Get all todos
app.get('/api/todos', (req, res) => {
  res.json({
    success: true,
    data: todos,
    count: todos.length
  });
});

// Get single todo
app.get('/api/todos/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const todo = todos.find(t => t.id === id);

  if (!todo) {
    return res.status(404).json({
      success: false,
      error: 'Todo not found'
    });
  }

  res.json({
    success: true,
    data: todo
  });
});

// Create todo
app.post('/api/todos', (req, res) => {
  const { title } = req.body;

  if (!title || title.trim() === '') {
    return res.status(400).json({
      success: false,
      error: 'Title is required'
    });
  }

  const newTodo = {
    id: nextId++,
    title: title.trim(),
    completed: false,
    createdAt: new Date().toISOString()
  };

  todos.push(newTodo);

  res.status(201).json({
    success: true,
    data: newTodo
  });
});

// Update todo
app.put('/api/todos/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const { title, completed } = req.body;

  const todoIndex = todos.findIndex(t => t.id === id);

  if (todoIndex === -1) {
    return res.status(404).json({
      success: false,
      error: 'Todo not found'
    });
  }

  if (title !== undefined) {
    todos[todoIndex].title = title.trim();
  }

  if (completed !== undefined) {
    todos[todoIndex].completed = completed;
  }

  todos[todoIndex].updatedAt = new Date().toISOString();

  res.json({
    success: true,
    data: todos[todoIndex]
  });
});

// Delete todo
app.delete('/api/todos/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const todoIndex = todos.findIndex(t => t.id === id);

  if (todoIndex === -1) {
    return res.status(404).json({
      success: false,
      error: 'Todo not found'
    });
  }

  const deletedTodo = todos.splice(todoIndex, 1)[0];

  res.json({
    success: true,
    data: deletedTodo
  });
});

// Clear completed todos
app.delete('/api/todos/completed/clear', (req, res) => {
  const beforeCount = todos.length;
  todos = todos.filter(t => !t.completed);
  const deletedCount = beforeCount - todos.length;

  res.json({
    success: true,
    message: `Deleted ${deletedCount} completed todos`,
    deletedCount
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`\n🚀 Express Todo API Server`);
  console.log(`📍 Server running on http://localhost:${PORT}`);
  console.log(`🏥 Health check: http://localhost:${PORT}/health`);
  console.log(`📝 API docs: http://localhost:${PORT}/api/todos`);
  console.log(`\n✨ Deployed with Deplight Platform\n`);
});
