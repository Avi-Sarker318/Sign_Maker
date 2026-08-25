# Sign Maker

Makes barcode sign PDFs, ready to print, from a simple list of labels.
Handles two kinds of signs - **Sticky Signs** (small, two per sheet) and
**Hanging Signs** (big, one full sheet each) - in one app. Built for people
who don't want to think about computers — just pick a type and follow three
steps.

## How to get it (one time only)

1. Go to this repo's **Releases** page (link on the right side of the GitHub
   page, or ask whoever shared this with you for the link).
2. Under the newest release, click **SignMaker.exe** to download it.
3. Move it into a folder you'll remember, e.g. your Desktop.

No installation, no Python, nothing else to set up. It's one file.

> Windows may show a blue "Windows protected your PC" warning the first time,
> because the file isn't digitally signed. Click **More info**, then
> **Run anyway**. This is normal for free, unsigned tools.

## How to use it

Double-click **SignMaker.exe**.

### First: what are you making?

At the top of the window, click **Sticky Signs** or **Hanging Signs**. You
can switch between them anytime - each one remembers its own list of labels
separately, so switching back and forth never mixes them up or loses
anything.

- **Sticky Signs** - small labels, two per printed sheet.
- **Hanging Signs** - big overhead signs, one per printed sheet.

Then follow the three steps below - they work the same way for both:

### Step 1 · Add your sign labels

- Under **Starts with**, type or pick what the sign begins with (like `a`).
- Under **Number**, type a number (like `001`).
- Click **+ Add**. It appears in the list, and the Number box is
  automatically set to the next one — so you can just keep clicking **+ Add**
  to make `a-001`, `a-002`, `a-003`, and so on.
- Want a whole batch at once? Also fill in **Up to** (e.g. Number `001`,
  Up to `010`) and click **+ Add** — that's ten signs in one click.
- Made a mistake? Click an item in the list and press **Remove selected**,
  or **Remove all** to start over.

Signs that "start with" the same thing (like `a`) are grouped together into
one PDF automatically. As you type, a **live preview** below shows exactly
what that sign will look like — to scale, matching whichever type you picked
above — so you can check it before printing anything.

### Step 2 · Choose where to save

You can usually skip this — it already picks a sensible folder for you.
Only click **Choose folder...** if you want the PDFs saved somewhere specific.
Sticky Signs and Hanging Signs are saved into separate, clearly named
folders, so they never get mixed up even if you save both to the same place.

### Step 3 · Make your signs

Click the big green **Create My Signs** button. When it's done, a message
turns green and the folder with your finished PDFs opens automatically.
If it doesn't, click **Open my files**.

That's it — your signs are ready to print.

### Adding more to a set you already made

You don't have to start over. If you made signs `2-001` through `2-030`
last week and now need `2-031` through `2-035` — or even need to go back
and fill in a range you skipped, like `2-036` through `2-039` — just:

1. Open the app and pick the same sign type. Your previous labels are still
   there, exactly where you left them.
2. Use Quick Add to add the new ones.
3. Click **Create My Signs** again.

You'll get one PDF with everything in it, correctly sorted by number (not
by the order you added things), and it replaces the older version — nothing
gets duplicated or left behind in another folder.

If you ever want to start a completely different set of signs from scratch,
click **Remove all** first — that clears the list for whichever type is
currently selected, and forgets it for next time too.

## Something not working?

- If the app won't open, make sure you clicked **Run anyway** on the Windows
  warning (see above).
- If nothing gets created, check the numbers you typed and try again — the
  message on screen will explain what happened.
- Curious what's happening behind the scenes? Click **Show technical
  details** near the bottom of the window for a full log.
- Not on Windows, or can't install anything? Ask whoever set this up for
  your team for the **"Latest Sticky Signs"** or **"Latest Hanging Signs"**
  link on GitHub instead — the same PDFs are also available there with
  nothing to install, from any device.
- For anything else, contact whoever set this up for your team.
