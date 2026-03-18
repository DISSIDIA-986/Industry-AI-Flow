# Industry AI Flow Front-end component library

## Overview

This is a for Industry AI Flow Modernization of project construction React Component library, based on Next.js and TypeScript development. The component library provides a complete UI A collection of components for building enterprise-level application interfaces.

## Component directory structure

```
src/components/
├── index.ts              # Unified export of components
├── Navbar.tsx           # Navigation bar component
├── ProtectedRoute.tsx   # protected routing component
├── dashboard-shell.tsx  # Instrument panel housing components
├── app-config-context.tsx # Application configuration context
├── forms/              # form component
│   └── index.tsx
├── tables/             # Table component
│   └── index.tsx
├── cards/              # card component
│   └── index.tsx
├── modals/             # Modal component
│   └── index.tsx
├── feedback/           # feedback component
│   └── index.tsx
├── files/              # file component
│   └── index.tsx
└── charts/             # chart component
    └── index.tsx
```

## Component usage example

### 1. form component

```tsx
import { Form, FormGroup, Input, Select, Button } from '@/components'

function ExampleForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    category: ''
  })

  return (
    <Form onSubmit={handleSubmit}>
      <FormGroup label="Name" required>
        <Input
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        />
      </FormGroup>
      
      <FormGroup label="Mail">
        <Input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        />
      </FormGroup>
      
      <FormGroup label="category">
        <Select
          value={formData.category}
          onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          options={[
            { value: 'option1', label: 'Option 1' },
            { value: 'option2', label: 'Option 2' }
          ]}
        />
      </FormGroup>
      
      <Button type="submit">submit</Button>
    </Form>
  )
}
```

### 2. Table component

```tsx
import { Table, TableHead, TableHeader, TableBody, TableRow, TableCell, Pagination } from '@/components'

function ExampleTable() {
  const [currentPage, setCurrentPage] = useState(1)

  return (
    <>
      <Table>
        <TableHead>
          <TableRow>
            <TableHeader>name</TableHeader>
            <TableHeader>state</TableHeader>
            <TableHeader>schedule</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((item) => (
            <TableRow key={item.id}>
              <TableCell>{item.name}</TableCell>
              <TableCell>{item.status}</TableCell>
              <TableCell>{item.progress}%</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      <Pagination
        currentPage={currentPage}
        totalPages={5}
        onPageChange={setCurrentPage}
      />
    </>
  )
}
```

### 3. card component

```tsx
import { Card, CardHeader, CardTitle, CardContent, StatCard } from '@/components'

function ExampleCards() {
  return (
    <div className="grid grid-cols-4 gap-4">
      <StatCard
        title="Total number of items"
        value={42}
        change="+12%"
        trend="up"
      />
      
      <Card>
        <CardHeader>
          <CardTitle>Project details</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Card content */}
        </CardContent>
      </Card>
    </div>
  )
}
```

### 4. Modal component

```tsx
import { Modal, ConfirmModal, LoadingModal } from '@/components'

function ExampleModals() {
  const [showModal, setShowModal] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [showLoading, setShowLoading] = useState(false)

  return (
    <>
      <button onClick={() => setShowModal(true)}>Open modal box</button>
      
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Example modal box"
      >
        <p>Modal box content</p>
      </Modal>
      
      <ConfirmModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={handleConfirm}
        title="Confirm deletion"
        message="Are you sure you want to delete it?"
      />
      
      <LoadingModal
        isOpen={showLoading}
        title="loading"
        message="Please wait..."
      />
    </>
  )
}
```

### 5. File upload component

```tsx
import { FileUpload, FileList } from '@/components'

function ExampleFileUpload() {
  const [files, setFiles] = useState([])

  const handleFileSelect = (file) => {
    // Process files
  }

  const handleDelete = (id) => {
    setFiles(prev => prev.filter(file => file.id !== id))
  }

  return (
    <>
      <FileUpload
        onFileSelect={handleFileSelect}
        accept=".pdf,.doc,.docx"
        maxSize={10}
        label="Upload files"
      />
      
      <FileList
        files={files}
        onDelete={handleDelete}
      />
    </>
  )
}
```

### 6. feedback component

```tsx
import { Loading, ErrorDisplay, EmptyState, Skeleton, ProgressBar } from '@/components'

function ExampleFeedback() {
  return (
    <>
      {/* Loading status */}
      <Loading text="loading..." />
      
      {/* error display */}
      <ErrorDisplay
        title="something went wrong"
        message="Unable to load data"
        onRetry={handleRetry}
      />
      
      {/* Empty state */}
      <EmptyState
        title="No data yet"
        description="There is no content here yet"
      />
      
      {/* skeleton screen */}
      <Skeleton count={3} height="h-4" />
      
      {/* progress bar */}
      <ProgressBar
        value={65}
        label="Upload progress"
        showPercentage
      />
    </>
  )
}
```

## Style configuration

Component library usage Tailwind CSS For style management, all components follow consistent style specifications:

### color system
- Main color: `#3b82f6` (blue)
- Success color: `#10b981` (green)
- Warning color: `#f59e0b` (yellow)
- Danger color: `#ef4444` (red)
- Information color: `#8b5cf6` (Purple)

### spacing system
based on Tailwind spacing system, using standard 0.25rem Increment.

### Responsive design
All components support responsive design using Tailwind Breakpoint system:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

## best practices

### 1. Component import
It is recommended to use named imports to avoid importing the entire component library:

```tsx
// recommend
import { Button, Input, Form } from '@/components'

// Not recommended
import * as Components from '@/components'
```

### 2. type safety
All components use TypeScript Type definition to ensure type safety:

```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: React.ReactNode
}
```

### 3. Error handling
The component has a built-in error handling mechanism. It is recommended to add error handling in key operations:

```tsx
try {
  await handleSubmit()
} catch (error) {
  // use ErrorDisplay Component shows error
}
```

### 4. accessibility
All components are designed with accessibility in mind:
- Supports keyboard navigation
- appropriate ARIA Label
- high contrast color
- focus management

## Development Guide

### Add new component
1. Create component files in the corresponding directory
2. Implement component logic and styles
3. Add to TypeScript type definition
4. exist `index.ts` Export components in
5. Update component demo page

### Component testing
Every component should:
1. Handle various input states
2. Support keyboard interaction
3. Responsive design
4. Accessibility check

### style override
If you need to override component styles, you can use `className` property:

```tsx
<Button className="custom-class">button</Button>
```

## Demo page

access `/components-demo` View live demos and usage examples of all components.

## Change log

### v1.0.0 (2026-02-14)
- Initial release
- Contains components such as forms, tables, cards, modal boxes, feedback, file uploads, etc.
- complete TypeScript support
- Responsive design
- Accessibility optimization

## license

MIT License