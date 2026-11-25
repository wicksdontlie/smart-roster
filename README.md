# Smart Roster Management System

A production-oriented workforce roster management system for operations teams.

The application allows operations managers to:

- Manage employees
- Manage brands and processes
- Configure operating rules
- Maintain employee availability
- Generate monthly rosters
- Validate roster coverage
- Detect scheduling conflicts
- Analyze workload
- Manually reassign roster entries
- Revalidate changes
- Ask an AI-powered Roster Copilot questions about the roster

---

## Architecture

```text
                    Smart Roster
                         |
          +--------------+--------------+
          |                             |
          v                             v
   React Frontend                 FastAPI Backend
          |                             |
          |              +--------------+--------------+
          |              |              |              |
          v              v              v              v
       Vercel       OR-Tools       Validator       AI Agent
                         |              |              |
                         +--------------+              |
                                |                      |
                                v                      v
                         Supabase PostgreSQL       OpenRouter