# Testbench: Functional Checklist

Use this checklist to validate key behaviors.

## A. Authentication
- [ ] Auth page loads at `/auth`.
- [ ] Register validates:
  - [ ] First name max 20 chars
  - [ ] Email includes `@` and ends with `.com`
  - [ ] Password has min 8 chars, one uppercase, one digit
- [ ] Friendly error messages shown (not raw Firebase code strings).
- [ ] Login succeeds with valid credentials.

## B. Study Tracker
- [ ] Upload accepts `.pdf/.docx/.txt`.
- [ ] Paper title is auto-inferred from file/meta/text.
- [ ] Bank page displays questions.
- [ ] Timer works (start/stop).
- [ ] Answer textareas auto-save and restore on refresh.
- [ ] Submit for marking creates attempt and redirects to report.

## C. Reports
- [ ] Report page loads for attempt.
- [ ] Concept summary table visible and readable.
- [ ] Question-by-question table wraps long feedback correctly.
- [ ] Download report file works.
- [ ] Download PDF report works.

## D. Study Plan
- [ ] Exam add/edit/delete works.
- [ ] Exams within 14 days appear in planning section.
- [ ] Prioritized and strong concepts shown as grouped concepts.
- [ ] Tutorial/Exam Practice mode generates 2 open questions with answer boxes.
- [ ] On-the-go recap mode generates 5 MCQ questions.
- [ ] Recap MCQs can be graded and score shown.
- [ ] Practice answers/selections auto-save and restore.

## E. Mascot Sidebar
- [ ] Mascot image appears in sidebar.
- [ ] Mascot area is enlarged and readable.
- [ ] Mascot image fades and rotates every hour.
- [ ] Sidebar message rotates in sync with image.

## F. Theme and UI
- [ ] Light/dark/ocean themes readable.
- [ ] Layout responsive on narrower screens.

