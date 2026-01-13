import { useState } from "react";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [file, setFile] = useState(null);
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(false);
  const [templateId, setTemplateId] = useState(null);
  const [error, setError] = useState("");

  async function analyze() {
    setError("");
    setTemplateId(null);
    if (!file) return;

    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${API}/api/analyze`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setRules(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function generate() {
    setError("");
    if (!rules) return;

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rules),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setTemplateId(data.template_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function download() {
    if (!templateId) return;
    window.open(`${API}/api/download/${templateId}`, "_blank");
  }

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h2>ВКР MVP: Генератор шаблонов отчётов</h2>
      <p style={{ color: "#444" }}>
        Загрузить требования (.docx или .txt) → проанализировать → сгенерировать .docx шаблон.
      </p>

      <div style={{ padding: 16, border: "1px solid #ddd", borderRadius: 12 }}>
        <input
          type="file"
          accept=".docx,.txt"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button onClick={analyze} disabled={!file || loading}>
            Проанализировать
          </button>
          <button onClick={generate} disabled={!rules || loading}>
            Сгенерировать шаблон
          </button>
          <button onClick={download} disabled={!templateId}>
            Скачать .docx
          </button>
        </div>

        {loading && <p>Загрузка...</p>}
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </div>

      {rules && (
        <div style={{ marginTop: 20 }}>
          <h3>Найденные правила (MVP)</h3>
          <pre style={{ background: "#f6f6f6", padding: 16, borderRadius: 12 }}>
            {JSON.stringify(rules, null, 2)}
          </pre>
        </div>
      )}

      {templateId && (
        <p style={{ marginTop: 12 }}>
          Шаблон готов. Нажми <b>Скачать .docx</b>.
        </p>
      )}
    </div>
  );
}
