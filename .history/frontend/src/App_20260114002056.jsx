import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

function formatTs(ts) {
  try {
    const d = new Date(ts * 1000);
    return d.toLocaleString();
  } catch {
    return String(ts);
  }
}

export default function App() {
  const [file, setFile] = useState(null);
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(false);
  const [templateId, setTemplateId] = useState(null);
  const [error, setError] = useState("");

  // profiles + history
  const [profiles, setProfiles] = useState([]);
  const [history, setHistory] = useState([]);
  const [profileName, setProfileName] = useState("");

  const canGenerate = useMemo(() => !!rules && !loading, [rules, loading]);

  async function refreshSideData() {
    try {
      const [pRes, hRes] = await Promise.all([
        fetch(`${API}/api/profiles`),
        fetch(`${API}/api/history`),
      ]);
      if (pRes.ok) {
        const p = await pRes.json();
        setProfiles(p.items || []);
      }
      if (hRes.ok) {
        const h = await hRes.json();
        setHistory(h.items || []);
      }
    } catch {
      // не критично
    }
  }

  useEffect(() => {
    refreshSideData();
  }, []);

  function updateRule(key, value) {
    setRules((prev) => ({ ...prev, [key]: value }));
  }

  async function analyze() {
    setError("");
    setTemplateId(null);
    if (!file) return;

    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch(`${API}/api/analyze`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      setRules(data);

      await refreshSideData();
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

  function downloadDocx() {
    if (!templateId) return;
    window.open(`${API}/api/download/${templateId}`, "_blank");
  }

  // export/import JSON rules
  function exportRules() {
    if (!rules) return;
    const blob = new Blob([JSON.stringify(rules, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rules.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function importRulesFromFile(f) {
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result || ""));
        setRules(data);
        setTemplateId(null);
        setError("");
      } catch (e) {
        setError("Не удалось прочитать JSON: " + String(e));
      }
    };
    reader.readAsText(f, "utf-8");
  }

  // profiles
  async function saveCurrentAsProfile() {
    setError("");
    if (!rules) return;

    const name = profileName.trim();
    if (!name) {
      setError("Введите название профиля (например: Методичка кафедры ИТ 2025).");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, rules }),
      });
      if (!res.ok) throw new Error(await res.text());

      setProfileName("");
      await refreshSideData();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  function applyRules(r) {
    setRules(r);
    setTemplateId(null);
    setError("");
  }

  async function deleteProfile(profileId) {
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/profiles/${profileId}`, { method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      await refreshSideData();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 1100, margin: "30px auto", fontFamily: "system-ui" }}>
      <h2 style={{ marginBottom: 6 }}>ВКР: Генератор шаблонов отчётов (Этап 3)</h2>
      <p style={{ color: "#444", marginTop: 0 }}>
        Анализ требований (.docx/.txt/.pdf) → редактирование правил → генерация .docx.
        Плюс: профили, история, экспорт/импорт JSON.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
        {/* LEFT */}
        <div>
          <div style={{ padding: 16, border: "1px solid #ddd", borderRadius: 12 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <input
                type="file"
                accept=".docx,.txt,.pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />

              <button onClick={analyze} disabled={!file || loading}>
                Проанализировать
              </button>

              <button onClick={generate} disabled={!canGenerate}>
                Сгенерировать шаблон
              </button>

              <button onClick={downloadDocx} disabled={!templateId}>
                Скачать .docx
              </button>

              <button onClick={exportRules} disabled={!rules}>
                Экспорт JSON
              </button>

              <label style={{ display: "inline-block" }}>
                <span
                  style={{
                    display: "inline-block",
                    padding: "6px 10px",
                    border: "1px solid #aaa",
                    borderRadius: 8,
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                >
                  Импорт JSON
                </span>
                <input
                  type="file"
                  accept=".json"
                  style={{ display: "none" }}
                  onChange={(e) => importRulesFromFile(e.target.files?.[0])}
                />
              </label>
            </div>

            {loading && <p style={{ marginTop: 10 }}>Загрузка...</p>}
            {error && <p style={{ marginTop: 10, color: "crimson", whiteSpace: "pre-wrap" }}>{error}</p>}
            {templateId && <p style={{ marginTop: 10 }}>Шаблон готов — нажми “Скачать .docx”.</p>}
          </div>

          {rules && (
            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
                <h3 style={{ marginTop: 0 }}>Правила (редактируемые)</h3>

                <label>Шрифт</label>
                <input
                  style={{ width: "100%", marginBottom: 10 }}
                  value={rules.font_name ?? ""}
                  onChange={(e) => updateRule("font_name", e.target.value)}
                />

                <label>Размер шрифта (pt)</label>
                <input
                  type="number"
                  style={{ width: "100%", marginBottom: 10 }}
                  value={rules.font_size_pt ?? 14}
                  onChange={(e) => updateRule("font_size_pt", Number(e.target.value))}
                />

                <label>Межстрочный интервал</label>
                <input
                  type="number"
                  step="0.1"
                  style={{ width: "100%", marginBottom: 10 }}
                  value={rules.line_spacing ?? 1.5}
                  onChange={(e) => updateRule("line_spacing", Number(e.target.value))}
                />

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div>
                    <label>Левое поле (мм)</label>
                    <input
                      type="number"
                      style={{ width: "100%" }}
                      value={rules.margin_left_mm ?? 30}
                      onChange={(e) => updateRule("margin_left_mm", Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label>Правое поле (мм)</label>
                    <input
                      type="number"
                      style={{ width: "100%" }}
                      value={rules.margin_right_mm ?? 15}
                      onChange={(e) => updateRule("margin_right_mm", Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label>Верхнее поле (мм)</label>
                    <input
                      type="number"
                      style={{ width: "100%" }}
                      value={rules.margin_top_mm ?? 20}
                      onChange={(e) => updateRule("margin_top_mm", Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <label>Нижнее поле (мм)</label>
                    <input
                      type="number"
                      style={{ width: "100%" }}
                      value={rules.margin_bottom_mm ?? 20}
                      onChange={(e) => updateRule("margin_bottom_mm", Number(e.target.value))}
                    />
                  </div>
                </div>

                <div style={{ marginTop: 12 }}>
                  <label>
                    <input
                      type="checkbox"
                      checked={!!rules.page_numbering}
                      onChange={(e) => updateRule("page_numbering", e.target.checked)}
                    />{" "}
                    Нумерация страниц
                  </label>
                </div>

                <label style={{ display: "block", marginTop: 10 }}>Шрифт номера страницы (pt)</label>
                <input
                  type="number"
                  style={{ width: "100%" }}
                  value={rules.page_number_font_size_pt ?? 12}
                  onChange={(e) => updateRule("page_number_font_size_pt", Number(e.target.value))}
                />
              </div>

              <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
                <h3 style={{ marginTop: 0 }}>Что нашлось автоматически</h3>
                <pre style={{ background: "#f6f6f6", padding: 12, borderRadius: 12, overflowX: "auto" }}>
                  {JSON.stringify(rules.raw_matches ?? {}, null, 2)}
                </pre>

                <h3>Полный JSON</h3>
                <pre style={{ background: "#f6f6f6", padding: 12, borderRadius: 12, overflowX: "auto" }}>
                  {JSON.stringify(rules, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT */}
        <div>
          <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
            <h3 style={{ marginTop: 0 }}>Профили</h3>

            <div style={{ display: "flex", gap: 8 }}>
              <input
                style={{ flex: 1 }}
                placeholder="Название профиля"
                value={profileName}
                onChange={(e) => setProfileName(e.target.value)}
              />
              <button onClick={saveCurrentAsProfile} disabled={!rules || loading}>
                Сохранить
              </button>
            </div>

            <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
              {profiles.length === 0 && <div style={{ color: "#666" }}>Профилей пока нет.</div>}
              {profiles.map((p) => (
                <div
                  key={p.id}
                  style={{ border: "1px solid #eee", borderRadius: 10, padding: 10 }}
                >
                  <div style={{ fontWeight: 600 }}>{p.name}</div>
                  <div style={{ color: "#666", fontSize: 12 }}>Создан: {formatTs(p.created_at)}</div>
                  <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                    <button onClick={() => applyRules(p.rules)} disabled={loading}>
                      Применить
                    </button>
                    <button onClick={() => deleteProfile(p.id)} disabled={loading}>
                      Удалить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16, marginTop: 16 }}>
            <h3 style={{ marginTop: 0 }}>История анализов</h3>
            <div style={{ display: "grid", gap: 8 }}>
              {history.length === 0 && <div style={{ color: "#666" }}>История пока пустая.</div>}
              {history.map((h) => (
                <div
                  key={h.id}
                  style={{ border: "1px solid #eee", borderRadius: 10, padding: 10 }}
                >
                  <div style={{ fontWeight: 600 }}>{h.filename}</div>
                  <div style={{ color: "#666", fontSize: 12 }}>Дата: {formatTs(h.created_at)}</div>
                  <div style={{ marginTop: 8 }}>
                    <button onClick={() => applyRules(h.rules)} disabled={loading}>
                      Применить правила
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ color: "#666", fontSize: 12, marginTop: 10 }}>
            Профили и история хранятся локально в backend/storage/ (json-файлы).
          </div>
        </div>
      </div>
    </div>
  );
}
