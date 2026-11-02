# Pre-work: get ready for the AI Agents workshop (about 30–40 minutes)

Please do this **at home, before Session 1**. You only need a laptop, internet, and a Google account.
At the end you will see **All good!** and **Backup key works.** Then you are ready.

**Deadline:** [ORGANIZERS: date, e.g. Thursday 12 November]
**Questions and screenshots:** [ORGANIZERS: WhatsApp group link or email]

**Before you start:**
- **Use a personal Gmail account**, not your university account. University accounts often block these tools.
- **You must be 18 or older** to create the keys below (it is in the companies' terms). If you are under 18, skip Steps 1, 2 and 4, and follow the box **"Under 18?"** in Step 5: you will use the workshop's own model instead.
- **Need a new Google account?** Create it now, not on the day. Google may ask for your phone number.

---

## Step 1: Create your Groq key (about 7 minutes)

A "key" is a long password that lets our code use an AI model for free.

1. Open **https://console.groq.com/keys**
2. Sign in, for example with your **personal Gmail**. Accept the terms if asked.
3. Click **Create API Key**. Give it any name, for example `workshop`.
4. **Copy the key now** (it starts with `gsk_`). Groq shows it only once. Paste it into a private note **on this laptop**, for example Notepad. Do not send it to yourself in a chat: you will paste it into Colab in Step 4.

> Never post your key in a group chat or a screenshot. It is like a password.

## Step 2: Create your backup Google key (about 7 minutes)

If Groq has problems on the day, we switch to Google. This key is the backup.

1. Open **https://aistudio.google.com/apikey** and sign in with your **personal Gmail**.
2. Accept the terms if asked.
3. Click **Create API key**, even if a key is already listed: older keys may no longer work. If it asks you to choose a project, pick the one offered (or create one with any name).
4. Copy the new key and paste it into the same note.

## Step 3: Open the workshop notebook (about 3 minutes)

1. Open this link: **https://colab.research.google.com/github/1Baleid/tuwaiq-agent-workshop/blob/main/notebooks/00_setup.ipynb**
2. Look at the round picture at the top right of Colab: it must be your **personal Gmail**. If it is not, click it and switch account.

## Step 4: Put your keys in Colab "Secrets" (about 5 minutes)

Colab can keep your keys safely, so you never paste them into the code.

1. In the left bar of Colab, click the **key icon** (🔑, "Secrets").
2. Click **Add new secret**.
   - Name: `GROQ_API_KEY` (exactly like this: capital letters and underscores)
   - Value: paste your Groq key
   - Switch **Notebook access** on.
3. Click **Add new secret** again.
   - Name: `GEMINI_API_KEY`
   - Value: paste your Google key
   - Switch **Notebook access** on.

If Colab later asks you to **grant this notebook access** to a secret, click **Grant access**.

## Step 5: Run the notebook (about 10 minutes)

1. Click inside the first grey code box, then press **Shift + Enter**. The first time, Colab shows **"Warning: This notebook was not authored by Google"**. That is normal for our notebook: click **Run anyway**. Wait until the box finishes (a ✓ appears next to it).
2. Do the same for each code box, from top to bottom. **Stop before the part called "Plan B"**: that part is only for the workshop day. You will see download bars; that is normal.
3. The box under **"3. Smoke test"** checks your setup. It takes a minute or two the first time. At the end you should see:

   ```
   All good!
   ```
   If it ends with **Something is wrong** instead, find the line that says **FAIL** and look up its words in the table below.
4. The box under **"4. Check your backup key"** should print `Backup key works.` If it shows an error, wait a minute and run it again. If it still fails, you are still ready (Groq is the main model): just include the error in your screenshot.

> **Under 18?** You have no keys, so use the workshop's own model:
> 1. Before running anything, choose **Runtime → Change runtime type → T4 GPU → Save**. If Colab says it cannot connect to a GPU, connect without one: it still works, just more slowly.
> 2. Run the **first** code box only.
> 3. Scroll down to the part called **Plan B** and run its code box. It downloads a small AI model into
>    your Colab (about 5 minutes) and ends with **All good!**
>
> Tell the organizers you used Plan B.

**Done!** Take one screenshot that shows **All good!** and **Backup key works.** (or the backup error) and send it to the organizers (see the top of this page).

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `could not read the secret` | In Secrets, check there is a secret named **exactly** as in the message (`GROQ_API_KEY` or `GEMINI_API_KEY`) and that its **Notebook access** is on. Then run the same box again. |
| `Invalid API Key` (Groq), or `Please pass a valid API key` / `Invalid Auth key` (Google) | The key was copied wrongly. Create a new key (Groq: Step 1, Google: Step 2), replace the value of the secret in Secrets, and run the box again. |
| `RateLimitError` or `429` | Too many requests at once. Wait one minute and run the box again. |
| Any other error in the box **"4. Check your backup key"** (for example `ACCESS_TOKEN_TYPE_UNSUPPORTED`, `PERMISSION_DENIED` or `503`) | Wait one minute and run it again. If it still fails, you are still ready: include the error in your screenshot. |
| Your account "is not allowed", or "access restricted by your admin" | You are probably on your university account. Switch to your personal Gmail (round picture at the top right) and try again. |
| A page says you must be **18 or older**, or asks you to prove your age (ID or card) | Stop. Do not try to get around it. Follow the **Under 18?** box in Step 5 and tell the organizers. |
| `Unable to connect to the runtime` | Try a different network (for example your phone's hotspot), or turn off your VPN. |
| Anything else | Take a screenshot of the error and send it to the organizers (see the top of this page). Don't worry: helpers will fix it with you before Session 1. |

## Keep your keys safe

- Only put your keys in Colab **Secrets**, never in a code box, a chat or a screenshot.
- If you think someone saw your key, delete it on the page where you created it, create a new one, and replace it in Secrets.
- After Step 4 you can delete the note with your keys.
