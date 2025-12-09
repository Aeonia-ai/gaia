# CSS Style Guide and Layout Patterns



This guide documents our CSS class system and layout patterns to prevent UI breakages.

## 🚨 Critical Rules - NEVER BREAK THESE

### 1. Main Container Layout
```html
<!-- ✅ CORRECT: Simple flex container -->
<div class="flex h-screen bg-slate-900">
  <!-- content -->
</div>

<!-- ❌ WRONG: flex-col with md:flex-row breaks layout -->
<div class="flex flex-col md:flex-row h-screen bg-slate-900">
  <!-- This will display as columns and break the UI! -->
</div>
```

### 2. Loading Indicators Must Be Outside Swap Targets
```html
<!-- ✅ CORRECT: Indicator outside the swap target -->
<div id="loading-spinner" class="htmx-indicator">
  <div class="spinner"></div>
</div>
<div id="message-area">
  <form hx-post="/auth/login" 
        hx-target="#message-area" 
        hx-indicator="#loading-spinner">
    <!-- form content -->
  </form>
</div>

<!-- ❌ WRONG: Indicator inside swap target will disappear -->
<div id="message-area">
  <div id="loading-spinner" class="htmx-indicator">
    <div class="spinner"></div>
  </div>
  <form hx-post="/auth/login" hx-target="#message-area">
    <!-- form content -->
  </form>
</div>
```

## 📐 Layout Patterns

### Page Structure
```html
<!-- Standard page layout -->
<div class="flex h-screen bg-slate-900">
  <!-- Sidebar (if needed) -->
  <aside id="sidebar" class="w-64 bg-slate-800">
    <!-- sidebar content -->
  </aside>
  
  <!-- Main content -->
  <main class="flex-1 flex flex-col">
    <!-- header -->
    <header class="bg-slate-800 p-4">
      <!-- header content -->
    </header>
    
    <!-- scrollable content -->
    <div class="flex-1 overflow-y-auto p-4">
      <!-- main content -->
    </div>
  </main>
</div>
```

### Form Layout
```html
<!-- Standard form styling -->
<form class="space-y-4 max-w-md mx-auto">
  <div>
    <label class="block text-sm font-medium text-slate-300 mb-2">
      Email
    </label>
    <input type="email" 
           class="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg 
                  text-white placeholder-slate-400 
                  focus:outline-none focus:ring-2 focus:ring-purple-500">
  </div>
  
  <button type="submit" 
          class="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 
                 text-white font-medium rounded-lg 
                 transition-colors duration-200">
    Submit
  </button>
</form>
```

### Card/Container Pattern
```html
<!-- Standard card styling -->
<div class="bg-slate-800/50 backdrop-blur-lg rounded-xl p-6 shadow-xl 
            border border-slate-700/50">
  <h2 class="text-xl font-bold text-white mb-4">Title</h2>
  <p class="text-slate-300">Content</p>
</div>
```

## 🎨 Color Palette

Use only these colors for consistency:

### Primary Colors
- **Background**: `bg-slate-900` (main), `bg-slate-800` (secondary)
- **Text**: `text-white` (primary), `text-slate-300` (secondary), `text-slate-400` (muted)
- **Accent**: `purple-600` (primary action), `purple-500` (hover/focus)
- **Borders**: `border-slate-700` (default), `border-slate-600` (hover)

### Status Colors
- **Success**: `text-green-400`, `bg-green-500/20`
- **Error**: `text-red-400`, `bg-red-500/20`
- **Warning**: `text-yellow-400`, `bg-yellow-500/20`
- **Info**: `text-blue-400`, `bg-blue-500/20`

## 📏 Spacing Scale

Use consistent spacing values:

```
p-0   (0px)
p-1   (0.25rem / 4px)
p-2   (0.5rem / 8px)
p-3   (0.75rem / 12px)
p-4   (1rem / 16px)
p-5   (1.25rem / 20px)
p-6   (1.5rem / 24px)
p-8   (2rem / 32px)
p-10  (2.5rem / 40px)
p-12  (3rem / 48px)
```

## 🚫 Common Mistakes to Avoid

### 1. Responsive Breakpoint Issues
```html
<!-- ❌ WRONG: Changes layout structure on mobile -->
<div class="flex-col md:flex-row">
  <!-- This completely changes the layout direction -->
</div>

<!-- ✅ CORRECT: Adjust spacing/sizing only -->
<div class="flex gap-2 md:gap-4">
  <!-- Maintains layout, just adjusts spacing -->
</div>
```

### 2. Inconsistent Button Styling
```html
<!-- ❌ WRONG: Different button styles -->
<button class="bg-blue-500 p-2">Save</button>
<button class="bg-green-600 px-4 py-1">Submit</button>

<!-- ✅ CORRECT: Consistent button styling -->
<button class="gaia-button">Save</button>
<button class="gaia-button gaia-button-primary">Submit</button>
```

### 3. Custom Colors Outside Palette
```html
<!-- ❌ WRONG: Random colors -->
<div class="bg-orange-500 text-pink-300">

<!-- ✅ CORRECT: Use defined palette -->
<div class="bg-purple-600 text-white">
```

## 🧪 Testing UI Changes

Before committing any UI changes:

1. **Run layout tests**:
   ```bash
   pytest tests/web/test_ui_layout.py -v
   ```

2. **Check responsive behavior**:
   - Test at mobile (375px), tablet (768px), desktop (1280px)
   - Use browser dev tools responsive mode

3. **Verify HTMX interactions**:
   - Test all form submissions
   - Check loading indicators appear/disappear correctly
   - Ensure swapped content maintains layout

## 📱 Mobile-First Approach

Always design for mobile first:

```html
<!-- Start with mobile layout -->
<div class="p-4">
  <!-- Then add larger screen adjustments -->
  <div class="md:p-6 lg:p-8">
```

## 🎯 Component Classes

### Gaia Design System Classes

```css
/* Buttons */
.gaia-button {
  @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200;
}

.gaia-button-primary {
  @apply bg-purple-600 hover:bg-purple-700 text-white;
}

.gaia-button-secondary {
  @apply bg-slate-700 hover:bg-slate-600 text-white;
}

/* Inputs */
.gaia-input {
  @apply w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg 
         text-white placeholder-slate-400 
         focus:outline-none focus:ring-2 focus:ring-purple-500;
}

/* Cards */
.gaia-card {
  @apply bg-slate-800/50 backdrop-blur-lg rounded-xl p-6 shadow-xl 
         border border-slate-700/50;
}
```

## 🔍 Visual Regression Testing

To catch visual changes:

1. **Take screenshots before changes**:
   ```bash
   python scripts/capture-ui-snapshots.py
   ```

2. **Make your changes**

3. **Compare snapshots**:
   ```bash
   python scripts/compare-ui-snapshots.py
   ```

## 📋 PR Checklist for UI Changes

- [ ] Run `pytest tests/web/test_ui_layout.py`
- [ ] Test on mobile, tablet, and desktop sizes
- [ ] Check loading indicators work correctly
- [ ] Verify color palette compliance
- [ ] Test with HTMX debug logging enabled
- [ ] Take before/after screenshots for review
- [ ] Update this guide if adding new patterns

## 🚨 Emergency Fixes

If the UI breaks in production:

1. **Revert to last working commit**:
   ```bash
   git revert HEAD
   git push
   ```

2. **Check browser console for errors**

3. **Common quick fixes**:
   - Remove `flex-col md:flex-row` patterns
   - Check loading indicators are outside swap targets
   - Verify all Tailwind classes are valid
   - Check for missing closing tags

## 📚 Resources

- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [HTMX Reference](https://htmx.org/reference/)
- [FastHTML Components](https://fasthtml.dev/components)
- [Our HTMX Debugging Guide](htmx-fasthtml-debugging-guide.md)