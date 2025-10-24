# React Integration Example

This directory contains a complete React component that demonstrates how to integrate with the Gmail ML Client REST API.

## Files

- **`GmailClient.jsx`** - Main React component with full API integration
- **`GmailClient.css`** - Comprehensive styling for the component
- **`README.md`** - This file

## Features

The React component provides a complete UI for:

- 📊 **Dashboard** - System status and training data overview
- 🔮 **Predictions** - View and review email classifications
- 🧠 **Training** - Train the ML model with user feedback
- ⚡ **Actions** - Apply actions to Gmail (with dry-run option)

## Quick Start

### 1. Create a new React app
```bash
npx create-react-app gmail-client-ui
cd gmail-client-ui
```

### 2. Copy the component files
```bash
# Copy the component files to your React app
cp GmailClient.jsx src/
cp GmailClient.css src/
```

### 3. Update App.js
```jsx
import React from 'react';
import GmailClientApp from './GmailClient';
import './App.css';

function App() {
  return (
    <div className="App">
      <GmailClientApp />
    </div>
  );
}

export default App;
```

### 4. Start the API server
```bash
# In your Gmail ML Client directory
python api.py
```

### 5. Start the React app
```bash
# In your React app directory
npm start
```

Visit http://localhost:3000 to see the Gmail ML Client UI!

## API Integration

The component includes a complete `GmailClientAPI` class that handles all REST API communication:

```javascript
const api = new GmailClientAPI('http://localhost:8000');

// Initialize the system
await api.initialize();

// Sync emails
await api.syncEmails(null, 100);

// Get predictions
const predictions = await api.getPredictions(50);

// Review a message
await api.reviewMessage('msg_123', 'Work');

// Train the model
await api.trainModel(6);

// Apply actions
await api.applyActions(true, 100); // dry run
```

## Component Features

### Dashboard Tab
- System status indicator
- Quick action buttons
- Training data statistics
- Label distribution chart

### Predictions Tab
- Email prediction cards
- Spam score and confidence indicators
- One-click review functionality
- Action type visualization

### Training Tab
- Training data statistics
- Model training controls
- Progress feedback
- Training tips and recommendations

### Actions Tab
- Dry run preview
- Live action application
- Safety warnings and guidelines
- Action result feedback

## Customization

### Styling
Modify `GmailClient.css` to match your design system:
- Color scheme in CSS custom properties
- Component spacing and layout
- Responsive breakpoints

### API Configuration
Update the API base URL in `GmailClient.jsx`:
```javascript
const API_BASE_URL = 'http://your-api-server:8000';
```

### Additional Features
The component is designed to be extensible. You can easily add:
- Real-time updates with WebSockets
- Email preview functionality
- Bulk operations
- Custom label management
- Advanced filtering and search

## Error Handling

The component includes comprehensive error handling:
- Network errors
- API validation errors
- User feedback for all operations
- Loading states and indicators

## Security Considerations

- API calls use proper CORS headers
- No sensitive data stored in component state
- Error messages don't leak internal details
- All Gmail operations go through the API layer

## Performance Tips

- Use React.memo for expensive components
- Implement pagination for large prediction lists
- Add debouncing for real-time search
- Cache API responses where appropriate

## Browser Compatibility

The component uses modern JavaScript features and requires:
- ES6+ support
- Fetch API
- CSS Grid and Flexbox

For older browsers, consider adding polyfills.

## Next Steps

1. **Authentication**: Add user authentication if deploying publicly
2. **Real-time Updates**: Implement WebSocket connections for live updates
3. **Mobile Optimization**: Enhance responsive design for mobile devices
4. **Offline Support**: Add service worker for offline functionality
5. **Testing**: Add unit and integration tests
6. **Deployment**: Set up CI/CD pipeline for production deployment

## Troubleshooting

### CORS Issues
If you encounter CORS errors:
1. Ensure the API server is running
2. Check that the React dev server URL is in the CORS allowlist
3. Verify the API base URL is correct

### API Connection Issues
- Check that the API server is running on port 8000
- Verify the Gmail credentials are set up correctly
- Check the browser console for detailed error messages

### Styling Issues
- Ensure `GmailClient.css` is imported correctly
- Check for CSS conflicts with other stylesheets
- Verify responsive breakpoints work on your target devices
