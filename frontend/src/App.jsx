import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";

// All the text on the page, in one place.
const t = {
  welcomeTo: "Welcome to",
  appName: "KFUPM Assistant",
  intro: "Ask about rules, courses, grading or deadlines. Answers come only from KFUPM documents, with sources.",
  placeholder: "Ask about KFUPM...",
  sources: "Sources",
  send: "Send",
  error: "Error: ",
  searching: "Searching the documents",
};

const SUGGESTIONS = [
  "How many hours is one credit?",
  "What counts as academic dishonesty?",
  "When does the add/drop period end?",
];

// One soft spring for everything, so all motion feels like the same family.
const spring = { type: "spring", stiffness: 320, damping: 30, mass: 0.8 };

export default function App() {
  const [messages, setMessages] = useState([]); // {id, role: "user"|"bot", text, sources, seconds, tools, error}
  const [history, setHistory] = useState([]); // the agent's memory, sent back with each question
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const chatting = messages.length > 0;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function ask(question) {
    if (!question.trim() || busy) return;
    setInput("");
    setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", text: question }]);
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || res.statusText);
      setHistory(data.history);
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "bot", text: data.answer,
        sources: data.sources, seconds: data.seconds, tools: data.tools }]);
    } catch (e) {
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: "bot", text: t.error + e.message, error: true }]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="app">
        {/* Decorative stripes, like the KFUPM Student App. They step back once a conversation starts. */}
        <motion.div className="stripes stripes-top" animate={{ opacity: chatting ? 0.35 : 1 }} transition={{ duration: 0.6 }}>
          <Stripes seed={7} cols={20} color="var(--teal-light)" />
        </motion.div>
        <motion.div className="stripes stripes-bottom" animate={{ opacity: chatting ? 0.12 : 1 }} transition={{ duration: 0.6 }}>
          <Stripes seed={3} cols={22} color="var(--teal-dark)" delay={0.25} />
        </motion.div>

        <header>
          <AnimatePresence>
            {chatting && (
              <motion.span className="brand" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }} transition={spring}>
                {t.appName}
              </motion.span>
            )}
          </AnimatePresence>
        </header>

        <main className="chat">
          <AnimatePresence mode="popLayout">
            {!chatting && <Welcome key="welcome" onPick={ask} />}
          </AnimatePresence>

          <AnimatePresence initial={false}>
            {messages.map((m) => <Message key={m.id} msg={m} />)}
            {busy && <Typing key="typing" label={t.searching} />}
          </AnimatePresence>
          <div ref={endRef} />
        </main>

        <motion.form
          className="composer"
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ ...spring, delay: 0.2 }}
          onSubmit={(e) => { e.preventDefault(); ask(input); }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t.placeholder}
            dir="auto"
            autoFocus
          />
          <motion.button
            type="submit"
            disabled={busy || !input.trim()}
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.95 }}
            transition={spring}
          >
            {t.send}
          </motion.button>
        </motion.form>
      </div>
    </MotionConfig>
  );
}

// Slanted bars in broken segments, drawn from a fixed seed so they look the same on every visit.
function Stripes({ seed, cols, color, delay = 0 }) {
  const bars = useMemo(() => {
    let s = seed;
    const rnd = () => (s = (s * 9301 + 49297) % 233280) / 233280;
    const out = [];
    for (let c = 0; c < cols; c++) {
      let y = Math.round(rnd() * 120);
      const segments = 1 + Math.floor(rnd() * 3);
      for (let k = 0; k < segments; k++) {
        const h = 60 + Math.round(rnd() * 160);
        out.push({ x: 40 + c * 22, y, h, w: rnd() > 0.7 ? 14 : 9, col: c });
        y += h + 8 + Math.round(rnd() * 18);
      }
    }
    return out;
  }, [seed, cols]);

  return (
    <svg viewBox={`0 0 ${cols * 22 + 120} 520`} aria-hidden="true">
      <g transform="skewX(-10) translate(60 0)">
        {bars.map((b, i) => (
          <motion.g
            key={i}
            initial={{ opacity: 0, y: 60 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: delay + b.col * 0.035 }}
          >
            <rect x={b.x} y={b.y} width={b.w} height={b.h} fill={color} />
          </motion.g>
        ))}
      </g>
    </svg>
  );
}

function Welcome({ onPick }) {
  return (
    <motion.div
      className="welcome"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12, transition: { duration: 0.25 } }}
      transition={{ ...spring, delay: 0.35 }}
    >
      <p className="welcome-to">{t.welcomeTo}</p>
      <h1>{t.appName}</h1>
      <p className="intro">{t.intro}</p>
      <motion.div className="suggestions" initial="hidden" animate="show"
        variants={{ show: { transition: { staggerChildren: 0.08, delayChildren: 0.55 } } }}>
        {SUGGESTIONS.map((s) => (
          <motion.button
            key={s}
            dir="ltr"
            variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: spring } }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onPick(s)}
          >
            {s}
          </motion.button>
        ))}
      </motion.div>
    </motion.div>
  );
}

function Message({ msg }) {
  const [open, setOpen] = useState(false);
  const side = msg.role === "user" ? 1 : -1; // slide in from the side the bubble sits on
  return (
    <motion.div
      layout
      className={`msg ${msg.role}${msg.error ? " error" : ""}`}
      initial={{ opacity: 0, y: 14, scale: 0.97, x: 12 * side }}
      animate={{ opacity: 1, y: 0, scale: 1, x: 0 }}
      transition={spring}
    >
      <div className="text" dir="auto">{msg.text}</div>

      {msg.sources?.length > 0 && (
        <div className="sources">
          <button className="toggle" onClick={() => setOpen((o) => !o)}>
            <motion.span animate={{ rotate: open ? 90 : 0 }} transition={spring} className="chev">›</motion.span>
            {t.sources} ({msg.sources.length})
          </button>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                className="source-list"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
              >
                {msg.sources.map((s, i) => (
                  <motion.div key={s.id} className="src" initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }} transition={{ ...spring, delay: 0.05 * i }}>
                    <b>{s.id}</b>
                    <span dir="auto">{s.text}</span>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {msg.seconds !== undefined && (
        <div className="meta">{msg.seconds}s{msg.tools?.length ? ` · ${msg.tools.join(", ")}` : ""}</div>
      )}
    </motion.div>
  );
}

function Typing({ label }) {
  return (
    <motion.div
      className="msg bot typing"
      initial={{ opacity: 0, y: 10, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
      transition={spring}
      role="status"
      aria-label={label}
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
        />
      ))}
    </motion.div>
  );
}
