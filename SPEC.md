# School Management System (SMS) - Technical Specification

## 1. Project Overview

**Project Name:** School Management System (SMS)
**Project Type:** Full-stack Web Application
**Core Functionality:** Comprehensive school administration platform with student management, attendance, grading, fee tracking, scheduling, library, transport, and parent portal
**Target Users:** Administrators, Teachers, Students, Parents

---

## 2. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 4.2+ (Python 3.10+) |
| Frontend | HTML5, Tailwind CSS 3.x |
| JavaScript | Alpine.js 3.x, HTMX 1.9.x |
| Database | SQLite (default), PostgreSQL (production) |
| Authentication | Django built-in auth with custom User model |

---

## 3. User Roles & Permissions

### Role Matrix

| Feature | Admin | Teacher | Student | Parent |
|---------|-------|---------|---------|--------|
| Dashboard | Full | Limited | Limited | Limited |
| Student Management | CRUD | Read | Own | Own Child |
| Teacher Management | CRUD | Read | - | - |
| Attendance | Full | Update | View Own | View Child |
| Grades | Full | Update | View Own | View Child |
| Fees | Full | - | View Own | View/Pay |
| Timetable | Full | Read/Update | Read | - |
| Library | Full | Update | Borrow | - |
| Transport | Full | - | View | View |
| Reports | Full | Limited | Own | Child |
| Settings | Full | - | - | - |

---

## 4. Database Models

### Core Models

```
User (AbstractBaseUser)
├── role: CharField (admin/teacher/student/parent)
├── phone: CharField
├── address: TextField
├── photo: ImageField
└── date_joined: DateTime

Student (AbstractUser)
├── user: OneToOne → User
├── admission_no: CharField (unique)
├── admission_date: DateField
├── date_of_birth: DateField
├── gender: CharField
├── blood_group: CharField
├── religion: CharField
├── aadhar_no: CharField
├── current_class: ForeignKey → Class
├── section: ForeignKey → Section
├── roll_number: IntegerField
├── house: CharField
├── parent: ForeignKey → Parent (null)
└── academic_year: ForeignKey → AcademicYear

Parent
├── user: OneToOne → User
├── student: ForeignKey → Student (ManyToMany)
├── occupation: CharField
├── income: DecimalField
├── relation: CharField
└── emergency_contact: CharField

Teacher
├── user: OneToOne → User
├── employee_id: CharField (unique)
├── department: ForeignKey → Department
├── qualification: CharField
├── experience: IntegerField
├── subjects: ManyToMany → Subject
└── designation: CharField

Class (Grade/Level)
├── name: CharField (e.g., "Class 10")
├── numeric_name: IntegerField
├── stream: CharField (Science/Commerce/Arts/null)
├── academic_year: ForeignKey → AcademicYear
└── capacity: IntegerField

Section
├── name: CharField (A, B, C...)
├── class: ForeignKey → Class
├── class_teacher: ForeignKey → Teacher
└── academic_year: ForeignKey → AcademicYear

Subject
├── name: CharField
├── code: CharField
├── subject_type: CharField (Core/Elective/Practical)
├── class: ForeignKey → Class
├── teacher: ForeignKey → Teacher
├── credit_hours: IntegerField
└── is_active: BooleanField

AcademicYear
├── name: CharField (e.g., "2025-26")
├── start_date: DateField
├── end_date: DateField
├── is_current: BooleanField
└── is_active: BooleanField

Department
├── name: CharField
├── code: CharField
└── hod: ForeignKey → Teacher

Attendance
├── student: ForeignKey → Student
├── date: DateField
├── status: CharField (Present/Absent/Late/Leave)
├── period: ForeignKey → Period (null)
├── marked_by: ForeignKey → Teacher
├── remarks: TextField
└── academic_year: ForeignKey → AcademicYear

Grade/Result
├── student: ForeignKey → Student
├── subject: ForeignKey → Subject
├── exam_type: ForeignKey → ExamType
├── marks: DecimalField
├── grade_letter: CharField
├── remarks: TextField
├── entered_by: ForeignKey → Teacher
├── academic_year: ForeignKey → AcademicYear
└── term: ForeignKey → Term

ExamType
├── name: CharField (Half-Yearly/Annual/Unit Test)
├── weightage: DecimalField
└── academic_year: ForeignKey → AcademicYear

Term
├── name: CharField (Term 1, 2, 3)
├── start_date: DateField
├── end_date: DateField
└── academic_year: ForeignKey → AcademicYear

FeeStructure
├── class: ForeignKey → Class
├── fee_type: ForeignKey → FeeType
├── amount: DecimalField
├── academic_year: ForeignKey → AcademicYear
├── due_date: DateField
└── is_active: BooleanField

FeeType
├── name: CharField (Tuition/Transport/Library)
├── category: CharField (Monthly/One-time)
└── description: TextField

FeePayment
├── student: ForeignKey → Student
├── fee_structure: ForeignKey → FeeStructure
├── amount_paid: DecimalField
├── payment_date: DateField
├── payment_mode: CharField (Cash/Cheque/Online)
├── transaction_id: CharField
├── receipt_no: CharField
├── fine: DecimalField
├── remarks: TextField
└── received_by: ForeignKey → Teacher

Timetable
├── class: ForeignKey → Class
├── section: ForeignKey → Section
├── period: ForeignKey → Period
├── subject: ForeignKey → Subject
├── teacher: ForeignKey → Teacher
├── day_of_week: IntegerField (0-6)
├── room_no: CharField
└── academic_year: ForeignKey → AcademicYear

Period
├── period_no: IntegerField
├── start_time: TimeField
├── end_time: TimeField
└── break: BooleanField

LibraryBook
├── isbn: CharField (unique)
├── title: CharField
├── author: CharField
├── publisher: CharField
├── category: CharField
├── rack_no: CharField
├── quantity: IntegerField
├── available: IntegerField
├── cost: DecimalField
└── cover_image: ImageField

LibraryTransaction
├── student: ForeignKey → Student
├── book: ForeignKey → LibraryBook
├── issue_date: DateField
├── due_date: DateField
├── return_date: DateField (null)
├── fine: DecimalField
├── status: CharField (Issued/Returned/Overdue)
└── issued_by: ForeignKey → Teacher

TransportRoute
├── route_no: CharField
├── vehicle_no: CharField
├── driver_name: CharField
├── driver_phone: CharField
├── stops: JSON (List of stops with timings)
└── fare: DecimalField

TransportAssignment
├── student: ForeignKey → Student
├── route: ForeignKey → TransportRoute
├── pickup_point: CharField
├── pickup_time: TimeField
└── academic_year: ForeignKey → AcademicYear

Message
├── sender: ForeignKey → User
├── receiver: ForeignKey → User
├── subject: CharField
├── message: TextField
├── is_read: BooleanField
├── parent_thread: ForeignKey → Message (null)
├── created_at: DateTime
└── read_at: DateTime

Notice
├── title: CharField
├── content: TextField
├── notice_type: CharField (General/Academic/Event)
├── posted_by: ForeignKey → User
├── for_roles: JSON (List of roles)
├── for_classes: ManyToMany → Class (null=all)
├── attachment: FileField
├── publish_date: DateField
├── expiry_date: DateField
└── is_active: BooleanField
```

---

## 5. Application Structure

### Django Apps

| App | Purpose |
|-----|---------|
| accounts | User authentication, profiles, roles |
| students | Student admission, records |
| academics | Classes, sections, subjects, timetable |
| attendance | Daily attendance tracking |
| examinations | Grades, exams, report cards |
| fees | Fee structure, payments |
| library | Book management, issuing |
| transport | Route, vehicle tracking |
| communications | Messages, notices |
| dashboard | Analytics, reporting |

---

## 6. URL Patterns

### Core URLs

```
/                           → Landing/Login
/dashboard/                 → Role-based dashboard
/accounts/login/            → Login
/accounts/logout/           → Logout
/accounts/profile/          → User profile

# Students
/students/                  → List all students
/students/add/              → Add new student (HTMX modal)
/student/<id>/              → Student detail
/student/<id>/edit/         → Edit student (HTMX modal)
/student/<id>/delete/       → Delete student
/students/search/           → Search students (HTMX)

# Teachers
/teachers/                  → List teachers
/teachers/add/              → Add teacher
/teacher/<id>/              → Teacher detail

# Attendance
/attendance/                → Mark attendance
/attendance/report/         → Attendance reports
/attendance/mark/<class>/   → Mark by class (HTMX)

# Grades
/grades/                    → Grade entry
/grades/report-card/        → Generate report card
/grades/<student>/          → Student grades

# Fees
/fees/structure/            → Fee structure
/fees/payment/              → Record payment
/fees/dues/                 → Fee dues list

# Library
/library/                   → Book list
/library/issue/             → Issue book
/library/return/            → Return book

# Transport
/transport/routes/          → Routes
/transport/assign/          → Student assignments

# Timetable
/timetable/                 → View timetable
/timetable/create/          → Create timetable

# Reports
/reports/                   → Report dashboard
/reports/export/            → Export data

# Settings
/settings/                  → System settings
```

---

## 7. Template Structure

```
templates/
├── base.html               → Base template with nav, footer
├── partials/
│   ├── header.html         → Navigation header
│   ├── sidebar.html        → Sidebar menu
│   ├── footer.html         → Footer
│   ├── modal.html          → HTMX modal template
│   ├── table.html          → Generic table
│   ├── form.html           → Generic form
│   ├── search.html         → Search form
│   ├── pagination.html     → Pagination
│   └── alerts.html         → Flash messages
├── registration/
│   ├── login.html          → Login page
│   └── password_change.html
├── dashboard/
│   ├── admin.html          → Admin dashboard
│   ├── teacher.html        → Teacher dashboard
│   ├── student.html        → Student dashboard
│   └── parent.html         → Parent dashboard
├── students/
│   ├── list.html           → Student list
│   ├── detail.html         → Student profile
│   ├── form.html           → Add/Edit form
│   └── report_card.html
├── teachers/
│   ├── list.html
│   ├── detail.html
│   └── form.html
├── attendance/
│   ├── mark.html           → Mark attendance
│   ├── report.html         → Attendance report
│   └── summary.html
├── grades/
│   ├── entry.html          → Grade entry form
│   ├── report_card.html
│   └── transcript.html
├── fees/
│   ├── structure.html
│   ├── payment.html
│   ├── receipt.html
│   └── dues.html
├── library/
│   ├── books.html
│   ├── issue.html
│   └── return.html
├── transport/
│   ├── routes.html
│   └── assignments.html
├── timetable/
│   ├── view.html
│   └── create.html
├── reports/
│   ├── index.html
│   ├── export.html
│   └── print/
│       ├── report_card.html
│       ├── id_card.html
│       └── certificate.html
└── errors/
    ├── 403.html
    ├── 404.html
    └── 500.html
```

---

## 8. HTMX Patterns

### Modal Form Pattern
```html
<!-- Trigger -->
<button hx-get="/students/add/" hx-target="#modal-container" 
        hx-swap="innerHTML" @click="openModal()">Add Student</button>

<!-- Modal Container -->
<div x-show="showModal" id="modal-container"></div>
```

### Table Update Pattern
```html
<!-- Search with HTMX -->
<input type="text" name="q" hx-get="/students/" 
        hx-trigger="keyup changed delay:300ms" 
        hx-target="#student-table" placeholder="Search...">

<!-- Table -->
<div id="student-table">
    {% include 'partials/table.html' %}
</div>
```

### Form Submission
```html
<form hx-post="/students/add/" hx-target="#student-list" 
      hx-swap="afterbegin" @submit="resetForm()">
```

---

## 9. Alpine.js Components

### Mobile Navigation
```html
<nav x-data="{ mobileMenu: false }">
    <button @click="mobileMenu = !mobileMenu">Toggle</button>
    <div x-show="mobileMenu">Menu Content</div>
</nav>
```

### Dropdown Menu
```html
<div x-data="{ open: false }">
    <button @click="open = !open">Menu</button>
    <ul x-show="open" @click.away="open = false">Items</ul>
</div>
```

### Form Validation
```html
<input x-model="name" @blur="$el.dataset.touched = true"
       :class="{ 'border-red-500': errors.name && $el.dataset.touched }">
```

### Modal Management
```html
<div x-data="{ showModal: false }">
    <div x-show="showModal" @keydown.escape="showModal = false">
        <!-- Modal content -->
    </div>
</div>
```

---

## 10. Features by Module

### 10.1 Student Management
- [ ] Admission form with photo upload
- [ ] Unique admission number generation
- [ ] Student profile with all details
- [ ] Search by name, admission no, class
- [ ] Filter by class, section, gender
- [ ] Bulk import from CSV
- [ ] Student ID card generation
- [ ] Transfer certificate generation
- [ ] Document upload (marksheet, TC)

### 10.2 Attendance
- [ ] Daily attendance marking
- [ ] Period-wise attendance
- [ ] Attendance by class/section
- [ ] Attendance reports (monthly, term)
- [ ] SMS notification for absent
- [ ] Leave request management
- [ ] Attendance percentage calculation

### 10.3 Grade Management
- [ ] Subject-wise grade entry
- [ ] Multiple exam types support
- [ ] Grade calculation (weighted)
- [ ] Report card generation
- [ ] Progress reports
- [ ] Grade comparison/ranking
- [ ] Merit list generation

### 10.4 Fee Management
- [ ] Fee structure by class
- [ ] Monthly/one-time fees
- [ ] Payment recording
- [ ] Receipt generation
- [ ] Fee due reminders
- [ ] Fine calculation
- [ ] Payment history
- [ ] Online payment link (stub)

### 10.5 Library
- [ ] Book catalog
- [ ] Book issue/return
- [ ] Due date tracking
- [ ] Fine calculation
- [ ] Book availability
- [ ] Member management

### 10.6 Transport
- [ ] Route management
- [ ] Vehicle details
- [ ] Student assignments
- [ ] Pickup point tracking
- [ ] Fee integration

### 10.7 Timetable
- [ ] Period scheduling
- [ ] Teacher assignment
- [ ] Room allocation
- [ ] Conflict detection
- [ ] View by class/teacher

### 10.8 Parent Portal
- [ ] View child attendance
- [ ] View grades
- [ ] View fee status
- [ ] Message teachers
- [ ] Receive notices

### 10.9 Dashboard & Reports
- [ ] Student count by class
- [ ] Attendance statistics
- [ ] Fee collection summary
- [ ] Library circulation
- [ ] Charts and graphs
- [ ] Export to PDF/Excel

---

## 11. Responsive Breakpoints (Tailwind)

| Breakpoint | Width | Devices |
|------------|-------|---------|
| sm | 640px | Large phones |
| md | 768px | Tablets |
| lg | 1024px | Laptops |
| xl | 1280px | Desktops |
| 2xl | 1536px | Large screens |

---

## 12. Color Scheme

```css
Primary:    #1E40AF (Blue-800)
Secondary:  #475569 (Slate-600)
Accent:     #059669 (Emerald-600)
Success:    #16A34A (Green-600)
Warning:    #D97706 (Amber-600)
Danger:     #DC2626 (Red-600)
Background: #F8FAFC (Slate-50)
Surface:    #FFFFFF
Text:       #1E293B (Slate-800)
Muted:      #64748B (Slate-500)
```

---

## 13. Implementation Priority

### Phase 1: Core Infrastructure
1. Django project setup
2. User authentication
3. Base templates with Tailwind
4. Student model and CRUD
5. Class/Section management

### Phase 2: Academic Modules
6. Subject management
7. Attendance system
8. Grade management
9. Timetable

### Phase 3: Operations
10. Fee management
11. Library system
12. Transport tracking

### Phase 4: Portal & Reports
13. Parent portal
14. Teacher dashboard
15. Reports & analytics
16. Export/Print features

---

## 14. Acceptance Criteria

- [ ] Users can register/login with role selection
- [ ] Admin can manage all entities
- [ ] Teachers can mark attendance and enter grades
- [ ] Students can view their own records
- [ ] Parents can view child progress
- [ ] All forms use HTMX for partial updates
- [ ] All pages are responsive
- [ ] Search and filter work on all lists
- [ ] Reports can be exported to PDF
- [ ] Print-friendly views for certificates
