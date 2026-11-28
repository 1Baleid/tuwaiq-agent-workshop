# Documents

34 public pages of King Fahd University of Petroleum & Minerals (KFUPM): the undergraduate
regulations (`01-01` to `01-16`), registrar pages (registration, calendars, exams, FAQs,
transcripts) and registrar notices. The same 34 documents come in three folders; `CORPUS_DIR` in
`config.py` picks which one the RAG reads.

| Folder | Files | What it is |
|---|---|---|
| `kfupm_raw/` | 33 `.txt` + 1 `.html` | **The default, used in the slides.** The text as one plain dump: no headings, lists or paragraphs. |
| `kfupm_structured/` | 34 `.md` | The same text as Markdown: one `## heading` section per complete rule. Use it with `CHUNK_BY_SECTION = True`. |
| `kfupm_pdf/` | 34 `.pdf` | The original pages, saved as PDF. |
| `deadlines.csv` | | The table behind the `get_deadline` tool (`name,date,note`, dates as `YYYY-MM-DD`). The add/drop, withdrawal, exam and registration dates come from the real calendar (`07_Academic_Calendar_Current_Semester`); the club fair and the scholarship are invented. One date is typed `03/12/2026` on purpose (Session 5, Fix 3). |

Switch folders in `config.py`, or without editing it: `CORPUS_DIR=data/kfupm_structured`.

## Notes

- `kfupm_structured/` keeps the wording of the rules. Tables (grades, calendars, timetables) are
  lists, rules the Registrar has since changed are marked `[UPDATED RULE]`, and places where the
  source page leaves a list out say so in square brackets.
- The older 2011/2012 edition of the undergraduate regulations is left out on purpose: both editions
  together would put the same rule in the results twice.
- `31_Replacement_Certificate.pdf` is a scan, so its PDF text is partly garbled. The `.txt` and `.md`
  copies were typed from the page images.
- `kfupm_raw/32_Transcripts_From_Outside_Dhahran.html` is an `.html` page on purpose: `rag.read_file()`
  does not read `.html` yet, so question q8 fails until Session 5, Fix 1 teaches the loader to read it.
- Keep personal or private data out of these folders: free LLM tiers may log what you send them.

## Sources

All pages retrieved on 2026-10-30. (c) King Fahd University of Petroleum & Minerals, public pages;
navigation, menus and footers removed.

| Document | Title | Source |
|---|---|---|
| `01-01_Academic_Regulations_And_Implementations` | Academic Regulations And Implementations | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-02_Admission_Of_New_Students` | Admission Of New Students | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-03_Academic_Regulations` | Academic Regulations | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-04_The_Academic_Levels_System` | The Academic Levels System | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-05_Attendance_And_Withdrawal` | Attendance And Withdrawal | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-06_Interruption_And_Suspension_Of_Enrollment` | Interruption And Suspension Of Enrollment | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-07_Re_Enrollment` | Re Enrollment | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-08_Graduation` | Graduation | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-09_Dismissal` | Dismissal | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-10_Study_By_Affiliation` | Study By Affiliation | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-11_Examinations_And_Grades` | Examinations And Grades | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-12_Final_Examination_Procedures` | Final Examination Procedures | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-13_Transfer` | Transfer | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-14_Visiting_Students` | Visiting Students | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-15_General_Rules` | General Rules | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `01-16_Appendices` | Appendices | [bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations](https://bulletin.kfupm.edu.sa/academic-regulations/undergraduate-regulations) |
| `03_Registration_Regulations` | Registration Regulations | [registrar.kfupm.edu.sa/registration/registration-regulations](https://registrar.kfupm.edu.sa/registration/registration-regulations) |
| `04_Registration_Violations` | Registration Violations | [registrar.kfupm.edu.sa/registration/registration-regulations](https://registrar.kfupm.edu.sa/registration/registration-regulations) |
| `05_Unified_Class_Level_Rule_Table` | Unified Class Level Rule Table | [registrar.kfupm.edu.sa/registration/unified-class-level-rule-table](https://registrar.kfupm.edu.sa/registration/unified-class-level-rule-table) |
| `06_Preparatory_Students_Freshmen_Courses` | Preparatory Students Freshmen Courses | [registrar.kfupm.edu.sa/registration/preparatory-students-eligible-for-taking-freshmen-courses](https://registrar.kfupm.edu.sa/registration/preparatory-students-eligible-for-taking-freshmen-courses) |
| `07_Academic_Calendar_Current_Semester` | Academic Calendar Current Semester | [registrar.kfupm.edu.sa/academic-calendar/current-semester](https://registrar.kfupm.edu.sa/academic-calendar/current-semester) |
| `08_Academic_Calendar_Next_Semester` | Academic Calendar Next Semester | [registrar.kfupm.edu.sa/academic-calendar/next-semester](https://registrar.kfupm.edu.sa/academic-calendar/next-semester) |
| `09_Early_Registration_Events_262-263` | Early Registration Events 262-263 | no URL (Registrar notice) |
| `12_Final_Exam_Guidelines` | Final Exam Guidelines | [registrar.kfupm.edu.sa/exams-grades/final-exam-guidelines](https://registrar.kfupm.edu.sa/exams-grades/final-exam-guidelines) |
| `15_FAQ_Registration` | FAQ Registration | [registrar.kfupm.edu.sa/faq/faq-registration](https://registrar.kfupm.edu.sa/faq/faq-registration) |
| `16_FAQ_Early_Registration` | FAQ Early Registration | [registrar.kfupm.edu.sa/faq/faq-early-registration](https://registrar.kfupm.edu.sa/faq/faq-early-registration) |
| `17_FAQ_Student_Educational_Planner` | FAQ Student Educational Planner | [registrar.kfupm.edu.sa/faq/faq-student-educational-planner](https://registrar.kfupm.edu.sa/faq/faq-student-educational-planner) |
| `18_FAQ_Summer_Term_Courses` | FAQ Summer Term Courses | [registrar.kfupm.edu.sa/faq/faq-course-offerings-in-summer-term](https://registrar.kfupm.edu.sa/faq/faq-course-offerings-in-summer-term) |
| `26_Honors_Revision_Notice` | Honors Revision Notice | no URL (Registrar notice) |
| `27_Freshman_Level_Restriction` | Freshman Level Restriction | no URL (Registrar notice) |
| `28_Minimum_Load_13_Credit_Hours` | Minimum Load 13 Credit Hours | no URL (Registrar notice) |
| `30_Transcript_Information` | Transcript Information | no URL (Registrar notice) |
| `31_Replacement_Certificate` | Replacement Certificate | no URL (Registrar notice) |
| `32_Transcripts_From_Outside_Dhahran` | Transcripts From Outside Dhahran | [registrar.kfupm.edu.sa/transcripts-certificates/how-to-request-transcripts-from-outside-dhahran](https://registrar.kfupm.edu.sa/transcripts-certificates/how-to-request-transcripts-from-outside-dhahran) |
