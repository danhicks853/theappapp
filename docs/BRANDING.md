# TheAppApp Branding Guide

## Official Product Names

### The Product Hierarchy

1. **TheAppApp** - The main application
   - Full name: "TheAppApp"
   - What it is: AI agent orchestration platform
   - Example: "Welcome to TheAppApp"

2. **TheAppApp App** - The package manager/installer  
   - Full name: "TheAppApp App"
   - What it is: Core agent installation and management system
   - Example: "Install TheAppApp App to get started"

3. **TheAppApp App Store** - The marketplace
   - Full name: "TheAppApp App Store"
   - What it is: Catalog of pre-built specialist templates
   - Example: "Browse TheAppApp App Store"

---

## The Recursive Naming

The naming is intentionally recursive and humorous:

- **TheAppApp** manages apps (projects)
- **TheAppApp App** is the app that manages TheAppApp's agents
- **TheAppApp App Store** is where you get TheAppApp Apps

It's funny, memorable, and technically accurate.

---

## Usage in UI

### Navigation
```
Dashboard
🏪 TheAppApp App Store       ← Browse and install specialists
👥 Installed Specialists      ← Manage your team
   (Meet the Team!)
📁 Projects
⚙️ Settings
```

### Buttons
- `[Browse TheAppApp App Store]` - Link to store
- `[Install TheAppApp App]` - Install a specialist from store
- `[Update Specialist]` - Update an installed specialist
- `[Remove Specialist]` - Remove from your team

### Headlines
- "Welcome to TheAppApp App Store"
- "Install TheAppApp App to expand your team"
- "Browse pre-built specialists in TheAppApp App Store"

---

## What NOT to Say

❌ "The AppAppApp Store" - Too many "App"s  
❌ "TheApp App Store" - Missing one "App"  
❌ "The AppApp Store" - Incorrect structure  
✅ "TheAppApp App Store" - Correct!

---

## Technical References

### API Routes
- `/api/v1/store/*` - TheAppApp App Store endpoints

### Service Names
- `StoreService` - Manages TheAppApp App Store
- `SpecialistService` - Manages specialists

### Database
- `specialists.template_id` - Links to store template
- `specialists.installed_from_store` - Boolean flag

---

## Messaging

### Marketing Copy
- "TheAppApp App Store - Where your agents get their coworkers"
- "Install new specialists. Expand your team."
- "From one app to many, recursively."

### User-Facing Text
- Keep it light and fun
- Embrace the recursive humor
- But make functionality crystal clear

---

## Employee of the Month

Fun easter egg widget showing a randomly selected specialist with a fake achievement quote.

Examples:
- "Outstanding SQL optimization work!"
- "Shipped 15 features without a single bug!"
- "Best code reviewer of the month!"

---

## Meet the Team

The specialist management page where:
- **Main Title:** "Installed Specialists"
- **Subtitle:** "Meet the Team!"
- Shows your installed specialists with personalities
- Shows built-in specialists available to install
- Employee of the Month widget at top

---

**Last Updated:** November 2, 2025
