# Running from Windows CMD

The project root is the directory containing `study.py`, `requirements.txt`, and `curriculum_engine`. Open that folder in Explorer, type `cmd` into the address bar, and press Enter. The folder name/location can contain spaces.

Run commands one at a time. Do not copy the `C:\...>` prompt. If you are viewing a ZIP, extract it before opening CMD. Files inside `curriculum_engine` are modules, not individual commands to launch.

```bat
py -m pip install -r requirements.txt
py study.py doctor
py study.py demo
py -m unittest discover -s tests -v
```

The first three commands install dependencies, inspect configuration, and run an offline prerecorded example. The test suite uses fake model responses.

For live generation, a key must be available to the current terminal. In CMD:

```bat
set "GROQ_API_KEY=YOUR_KEY_HERE"
```

That sets the current session only. If using `setx GROQ_API_KEY "YOUR_KEY_HERE"`, open a new terminal afterward. Never paste the real key into an issue, screenshot, commit, or chat export intended for the repository.

```bat
py study.py inspect --source "lecture.pdf"
py study.py generate --course "CS 245" --source "lecture.pdf" --pages 1-5 --max-output-tokens 3000
```

`inspect` shows local extraction; compare symbols with the PDF. The generation command uses the first five physical pages. Omit `--pages` for all material only after reviewing provider capacity and input size. `--topic "Structural induction"` narrows the requested topic within the supplied material. `--dry-run` checks inputs without API requests/output writes, and `--print` also displays the generated Markdown.

Repeat the exact generation command to resume/reuse checkpoints. Add `--regenerate` for a fresh separate run, which makes new requests. The terminal prints the actual output directory; open `lessons.md` for the text and `plan.json` for the teaching plan.

```bat
explorer output
```

For the priority workflow:

```bat
py study.py tasks --db "%USERPROFILE%\curriculum.db"
py study.py generate --db "%USERPROFILE%\curriculum.db" --assignment-id 1 --source "lecture.pdf"
```

Choose the actual database location, displayed assignment ID, and matching lecture. The package does not import deadlines itself. Keep the original priority script separately until it has been deliberately integrated.

Live requests can wait 65 seconds between successful calls in the patched client. HTTP 429 may still occur; the client follows a provided retry delay or a fallback and stops for long waits. A later HTTP 400 is a distinct error; read the provider message rather than treating it as another rate limit.

Current default limits include 24 request attempts per invocation, 90-second per-request timeout, 6,500 output tokens unless overridden, two format attempts including the original, three transport attempts, a 100,000-character prompt cap, and up to 12 lessons. These are implementation settings, not a spending guarantee or measured optimum.
