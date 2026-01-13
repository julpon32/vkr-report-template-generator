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

  function updateRule(key, value) {
    setRules((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div style={{ maxWidth: 950, margin: "40px auto", fontFamily: "system-ui" }}>
      <h2>ВКР: Генератор шаблонов отчётов (Этап 2)</h2>

      <div style={{ padding: 16, border: "1px solid #ddd", borderRadius: 12 }}>
        <input
          type="file"
          accept=".docx,.txt,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
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
        {error && <p style={{ color: "crimson", whiteSpace: "pre-wrap" }}>{error}</p>}
      </div>

      {rules && (
        <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
            <h3 style={{ marginTop: 0 }}>Правила (можно редактировать)</h3>

            <label>Шрифт</label>
            <input
              style={{ width: "100%", marginBottom: 10 }}
              value={rules.font_name}
              onChange={(e) => updateRule("font_name", e.target.value)}
            />

            <label>Размер шрифта (pt)</label>
            <input
              type="number"
              style={{ width: "100%", marginBottom: 10 }}
              value={rules.font_size_pt}
              onChange={(e) => updateRule("font_size_pt", Number(e.target.value))}
            />

            <label>Межстрочный интервал</label>
            <input
              type="number"
              step="0.1"
              style={{ width: "100%", marginBottom: 10 }}
              value={rules.line_spacing}
              onChange={(e) => updateRule("line_spacing", Number(e.target.value))}
            />

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div>
                <label>Левое поле (мм)</label>
                <input
                  type="number"
                  style={{ width: "100%" }}
                  value={rules.margin_left_mm}
                  onChange={(e) => updateRule("margin_left_mm", Number(e.target.value))}
                />
              </div>
              <div>
                <label>Правое поле (мм)</label>
                <input
                  type="number"
                  style={{ width: "100%" }}
                  value={rules.margin_right_mm}
                  onChange={(e) => updateRule("margin_right_mm", Number(e.target.value))}
                />
              </div>
              <div>
                <label>Верхнее поле (мм)</label>
                <input
                  type="number"
                  style={{ width: "100%" }}
                  value={rules.margin_top_mm}
                  onChange={(e) => updateRule("margin_top_mm", Number(e.target.value))}
                />
              </div>
              <div>
                <label>Нижнее поле (мм)</label>
                <input
                  type="number"
                  style={{ width: "100%" }}
                  value={rules.margin_bottom_mm}
                  onChange={(e) => updateRule("margin_bottom_mm", Number(e.target.value))}
                />
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <label>
                <input
                  type="checkbox"
                  checked={rules.page_numbering}
                  onChange={(e) => updateRule("page_numbering", e.target.checked)}
                />{" "}
                Нумерация страниц
              </label>
            </div>

            <label style={{ display: "block", marginTop: 10 }}>Шрифт номера страницы (pt)</label>
            <input
              type="number"
              style={{ width: "100%" }}
              value={rules.page_number_font_size_pt}
              onChange={(e) => updateRule("page_number_font_size_pt", Number(e.target.value))}
            />
          </div>

          <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
            <h3 style={{ marginTop: 0 }}>Что нашлось автоматически</h3>
            <pre style={{ background: "#f6f6f6", padding: 12, borderRadius: 12, overflowX: "auto" }}>
              {JSON.stringify(rules.raw_matches, null, 2)}
            </pre>

            <h3>Полный JSON</h3>
            <pre style={{ background: "#f6f6f6", padding: 12, borderRadius: 12, overflowX: "auto" }}>
              {JSON.stringify(rules, null, 2)}
            </pre>
          </div>
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
