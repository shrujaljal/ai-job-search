# Job Application Assistant for Shrujal Agarwal

## Role
This repo is a job application workspace. Claude acts as a career advisor and application assistant for Shrujal Agarwal, helping with:
1. **Job fit evaluation** - Assess job postings against her profile (skills, experience, behavioral traits)
2. **CV tailoring** - Adapt existing CV templates (LaTeX/moderncv) to target specific roles
3. **Cover letter writing** - Draft targeted cover letters using existing templates (LaTeX)
4. **Interview preparation** - Prepare answers, questions, and talking points for interviews
5. **Career strategy** - Advise on positioning and personal branding

## Candidate Profile

### Identity
- **Name:** Shrujal Agarwal
- **Location:** California, United States (open to relocation anywhere within the US)
- **Languages:** English
- **Status:** MBA graduate seeking full-time opportunities in the United States (requires H-1B sponsorship)
- **Positioning:** "An MBA graduate who combines analytics, operations, strategy, and communication to solve business problems, improve processes, and support better decision-making across cross-functional teams."

### Education
- **MBA** (Graduated June 2026) - University of California, Riverside (UCR) — GPA: 3.8
  - Honors: Beta Gamma Sigma Honor Society; 2024 Case Competition Winner
- **Bachelor of Technology in Biotechnology** - Vellore Institute of Technology (VIT), India

### Professional Experience
- **Teaching Assistant – Statistics** (Sep 2025 – Present) - **UC Riverside** (California)
  - Facilitated weekly graduate-level statistics lab sessions; mentored students on hypothesis testing, regression, t-tests, confidence intervals
  - Evaluated assignments, provided structured feedback, maintained grading consistency
  - Held office hours; simplified quantitative concepts through practical business examples

- **Analyst Intern – Operations & Marketing Strategy** (Feb 2025 – Sep 2025) - **BB Wellness** (Startup)
  - Tracked campaign performance and engagement metrics via Excel dashboards
  - Conducted competitive analysis across digital channels; synthesized findings for leadership
  - Coordinated cross-functional projects; maintained content calendars and project trackers
  - Trained interns on reporting workflows and documentation standards
  - Used AI tools (ChatGPT, Claude, Excel Copilot) to streamline recurring reporting

- **Analyst – Global Operations & Strategy** (Oct 2023 – Jun 2024) - **Thomson Reuters**
  - Analyzed operational and financial data using SQL and Advanced Excel to support reporting and business decisions
  - Developed KPI dashboards and reporting frameworks improving operational visibility across global teams
  - Managed SAP Ariba procurement workflows: purchase requisitions, PO validation, invoice review
  - Supported budgeting, forecasting, and variance analysis; prepared executive summaries
  - Standardized SOPs and documentation to improve governance and workflow consistency

- **STEM Intern – Asset & Wealth Management** (Feb 2023 – Jun 2023) - **Goldman Sachs**
  - Supported Client Revenue Operations (CRO) and Institutional Client Reporting (ICR) teams
  - Built Excel-based workflow trackers improving visibility into reporting progress
  - Contributed to commitment naming standardization project reducing reporting ambiguity
  - Analyzed manual vs. automated reporting workflows; proposed process improvements
  - Used Qlik Sense and JIRA for operational reporting and issue tracking

- **Data Analyst Intern** (Jun 2022 – Aug 2022) - **Beyond Key**
  - Retrieved and analyzed business data using SQL; developed Tableau dashboards for clients
  - Cleaned and validated datasets; identified trends supporting operational decisions
  - Applied Python (Pandas, NumPy) for data preparation and exploratory analysis

### Technical Skills
- **Primary:** Advanced Excel (Pivot Tables, XLOOKUP, Power Query, Copilot), SQL, Tableau, Business Analysis, Operational Reporting, KPI Dashboards
- **Secondary:** Python (Pandas, NumPy), Qlik Sense, SAP Ariba, JIRA, Power BI (working knowledge), Salesforce (CRM familiarity), Buffer, Canva
- **Domain:** Business Operations, Strategy & Operations, Process Improvement, Workflow Optimization, Stakeholder Management, Executive Reporting, Cross-functional Collaboration, Market Research, Competitive Analysis, Campaign Reporting, Financial Analysis, Governance
- **AI Tools:** ChatGPT, Claude, Gemini, NotebookLM, Microsoft Copilot, Excel Copilot, n8n

### Awards
- 2024 Case Competition Winner - UC Riverside / AGSM
- Beta Gamma Sigma Honor Society (GPA honors)

### Behavioral Profile
- **Working style:** Structured thinker — understands the problem before jumping to solutions; breaks ambiguity into components
- **Decision-making:** Clarifies objective → maps process → finds data → consults stakeholders → recommends practical solutions
- **Communication:** Clear, concise, business-oriented; prefers dashboards, executive summaries, and visual frameworks over lengthy documents
- **Leadership:** Collaborative, influence-without-authority; takes ownership of organizing, documenting, and driving execution
- **Strengths:** Structured problem solving, executive communication, business storytelling, cross-functional collaboration, analytical reasoning, process improvement, data interpretation
- **Growth areas:** Less interested in narrow technical specialization; building toward broader strategy/operations leadership
- **Thrives in:** Cross-functional environments with high visibility, analytical work, fast learning, and meaningful business impact

### What Excites Her
- Understanding how businesses operate — why processes are inefficient, why teams are misaligned, what information leadership is missing
- Taking ambiguous business problems and creating structure around them
- Connecting data, business context, and people to improve decision-making

### Target Sectors (Priority Order)
- **Priority 1:** Technology, Enterprise SaaS, AI, FinTech, Healthcare Technology
- **Priority 2:** Management Consulting (MBB, Big 4), Financial Services (GS, JPM, Amex, Visa)
- **Priority 3:** Consumer Technology, Healthcare/Biotech, Enterprise Software

### Target Role Families (Priority Order)
1. Strategy & Operations / Business Operations / Operations Analyst
2. Business Analyst / Strategy Analyst
3. Program Management / Business Program Manager
4. Product Marketing / Marketing Strategy / Marketing Operations
5. Consulting / Corporate Strategy / Operational Excellence

### Deal-breakers
- Roles requiring H-1B sponsorship rejection (prioritize known sponsors)
- Pure software engineering, machine learning, data science, or quant finance roles
- Heavy quota-carrying sales roles
- Roles with no cross-functional or strategic component

### MBA Projects (for resume use)
- **Hyundai Rotem Operations Consulting** — MBA consulting engagement; process mapping, stakeholder interviews, bottleneck analysis, phased implementation roadmap for LA Metro railcar manufacturing facility (strongest project for Strategy/Operations/Consulting/BA)
- **LinkedIn Ads Marketing Strategy** — B2B campaign strategy, customer segmentation, persona development, KPI selection (best for Marketing/Product Marketing)
- **Value Proposition Canvas** — Customer needs analysis, pain/gain mapping, positioning strategy (best for Product Marketing)
- **Roche vs. Illumina Strategic Analysis** — Competitive analysis, Porter's Five Forces, SWOT, strategic recommendations (best for Healthcare/Strategy/Consulting)
- **Root Beer Game** — Supply chain simulation, Bullwhip Effect, systems thinking (best for Operations/Supply Chain)
- **Hotelling Location Strategy** — Game theory, competitive positioning (supporting project for Strategy/Consulting)

### Leadership (MBA)
- **Professional Development Lead**, AGSM Student Association — Led ~20-member team; launched podcast initiative; improved student engagement with career content
- **Marketing & Communications Lead**, AGSM Student Association — Newsletters, communication calendars, student outreach
- **Marketing Director**, TEDx UCR — Led 25-member marketing team for university TEDx event; campaign planning and execution
- **Finance Director**, Women in Business Association — Budget planning, financial coordination
- **Operations Lead**, Make A Difference (MAD) — Volunteer coordination, workflow organization

## Git Workflow
- Always pull latest changes at the start of a session
- After any file modifications, stage all changes with `git add .`
- Write descriptive commit messages summarizing what changed and why
- Push to origin master after every commit
- Use `gh` for pull requests when working on feature branches

## Repo Structure
- `cv/` - LaTeX CV variants (moderncv template, banking style)
- `cover_letters/` - LaTeX cover letters (custom cover.cls template)
- `.claude/skills/` - AI skill definitions for the application workflow
- `.agents/skills/` - Job search CLI tools

## Workflow for New Job Applications
1. User provides a job posting (URL or text)
2. **Always evaluate fit first**: skills match, experience match, behavioral/culture match. Present this assessment to the user before proceeding.
3. If good fit: create targeted CV (`cv/main_<company>.tex`) and cover letter (`cover_letters/cover_<company>_<role>.tex`)
4. **Verify both documents** (see Verification Checklist below)
5. Prepare interview talking points based on the role requirements and your strengths

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.

## Verification Checklist
After creating or updating a CV or cover letter, re-read the generated file and verify **all** of the following before presenting to the user. Report the results as a pass/fail checklist.

### Factual accuracy
- [ ] All claims match actual profile (CLAUDE.md / candidate profile) - no fabricated skills, experience, or achievements
- [ ] Job titles, dates, company names, and locations are correct
- [ ] Contact details are correct
- [ ] All company-specific claims (partnerships, products, technology, expansions) have been independently verified via WebFetch/WebSearch - do not trust reviewer agent research without verification

### Targeting
- [ ] Profile statement / opening paragraph is tailored to the specific role (not generic)
- [ ] Skills and experience bullets are reframed to match the job requirements
- [ ] Key job requirements are addressed (with gaps acknowledged where relevant)
- [ ] Nice-to-have requirements are highlighted where there is a match

### Consistency
- [ ] CV follows the standard 2-page moderncv/banking format
- [ ] Cover letter uses cover.cls template and established structure
- [ ] Tone is consistent across CV and cover letter
- [ ] No contradictions between CV and cover letter content

### Quality
- [ ] No LaTeX syntax errors (balanced braces, correct commands)
- [ ] No spelling or grammar errors
- [ ] Agentic coding / AI tooling references mention **Claude Code** by name
- [ ] Cover letter is addressed to the correct person (or "Dear Hiring Manager" if unknown)
- [ ] Cover letter fits approximately one page

### Compiled PDF verification (MANDATORY - never skip)
Both documents MUST be compiled and visually inspected via the Read tool on the PDF output. "Looks fine in the .tex" is not acceptable - LaTeX page-break decisions are unpredictable. Iterate until these all pass:
- [ ] CV compiled with **lualatex** (pdflatex often fails on modern MiKTeX with fontawesome5 font-expansion errors). Cover letter compiled with **xelatex** (cover.cls requires fontspec).
- [ ] **CV is exactly 2 pages** - not 1, not 3
- [ ] **No orphaned `\cventry` titles** - a job/education title must never sit at the bottom of a page with its bullets spilling to the next page. Use `\needspace{5\baselineskip}` before each `\cventry` to prevent this, and `\enlargethispage{2-3\baselineskip}` to rescue a trailing section that just barely spills
- [ ] **Cover letter is exactly 1 page** - signature block must fit with the body, never overflow
- [ ] **Cover letter bullet font matches body font** - `\lettercontent{}` must not wrap `\begin{itemize}...\end{itemize}` (the command's trailing `\\` errors on `\end{itemize}`, and moving itemize outside loses the Raleway font). Standard pattern: close `\lettercontent{}`, then wrap the list in `{\raggedright\fontspec[Path = OpenFonts/fonts/raleway/]{Raleway-Medium}\fontsize{11pt}{13pt}\selectfont \begin{itemize}...\end{itemize}\par}`
