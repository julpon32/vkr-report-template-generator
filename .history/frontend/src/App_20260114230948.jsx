import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function formatTs(ts) {
  try {
    const d = new Date(ts * 1000);
    return d.toLocaleString();
  } catch {
    return String(ts);
  }
}

function showMoreHistory() {
  setHistoryShown((prev) => prev + 5);
}
function collapseHistory() {
  setHistoryShown(5);
}

export default function App() {
  const [file, setFile] = useState(null);
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(false);
  const [templateId, setTemplateId] = useState(null);
  const [error, setError] = useState("");
  const [profiles, setProfiles] = useState([]);
  const [history, setHistory] = useState([]);
  const [historyShown, setHistoryShown] = useState(5); // сколько старых записей показывать
  const [templates, setTemplates] = useState([]);
  const [profileName, setProfileName] = useState("");
  const canGenerate = useMemo(() => !!rules && !loading, [rules, loading]);

  async function refreshSideData() {
    try {
      const [pRes, hRes, tRes] = await Promise.all([
        fetch(`${API}/api/profiles`),
        fetch(`${API}/api/history`),
        fetch(`${API}/api/templates`),
      ]);

      if (pRes.ok) {
        const p = await pRes.json();
        setProfiles(p.items || []);
      }
      if (hRes.ok) {
        const h = await hRes.json();
        setHistory(h.items || []);
      }
      if (tRes.ok) {
        const t = await tRes.json();
        setTemplates(t.items || []);
      }
    } catch {
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
    <div className="appShell">
      <div className="container">
        <div className="header">
          <h1 className="title">ВКР: Генератор шаблонов отчётов</h1>
          <p className="subtitle">
            Анализ требований (.docx/.txt/.pdf) → редактирование правил → генерация .docx. Профили, история,
            экспорт/импорт JSON.
          </p>
        </div>

        <div className="grid">
          {/* LEFT */}
          <div>
            <div className="card">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div className="file">
                  <input
                    type="file"
                    accept=".docx,.txt,.pdf"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </div>
                <span className="badge">
                  Backend: {API.replace("http://", "")}
                </span>
              </div>

              <div className="spacer" />

              <div className="row">
                <button className="btn btnPrimary" onClick={analyze} disabled={!file || loading}>
                  Проанализировать
                </button>
                <button className="btn" onClick={generate} disabled={!canGenerate}>
                  Сгенерировать шаблон
                </button>
                <button className="btn" onClick={downloadDocx} disabled={!templateId}>
                  Скачать .docx
                </button>
                <button className="btn" onClick={exportRules} disabled={!rules}>
                  Экспорт JSON
                </button>

                <label className="btn" style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                  Импорт JSON
                  <input
                    type="file"
                    accept=".json"
                    style={{ display: "none" }}
                    onChange={(e) => importRulesFromFile(e.target.files?.[0])}
                  />
                </label>
              </div>

              {loading && <p className="msg">Загрузка…</p>}
              {error && <div className="msgError">{error}</div>}
              {templateId && <p className="msg">Шаблон готов — нажми “Скачать .docx”.</p>}
            </div>

            {rules && (
              <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div className="card">
                  <div className="cardTitle">Правила (редактируемые)</div>

                  <div className="field">
                    <label>Шрифт</label>
                    <input
                      className="input"
                      value={rules.font_name ?? ""}
                      onChange={(e) => updateRule("font_name", e.target.value)}
                    />
                  </div>

                  <div className="kvGrid" style={{ marginTop: 10 }}>
                    <div className="field">
                      <label>Размер шрифта (pt)</label>
                      <input
                        className="input"
                        type="number"
                        value={rules.font_size_pt ?? 14}
                        onChange={(e) => updateRule("font_size_pt", Number(e.target.value))}
                      />
                    </div>

                    <div className="field">
                      <label>Межстрочный интервал</label>
                      <input
                        className="input"
                        type="number"
                        step="0.1"
                        value={rules.line_spacing ?? 1.5}
                        onChange={(e) => updateRule("line_spacing", Number(e.target.value))}
                      />
                    </div>
                  </div>

                  <hr className="sep" />

                  <div className="kvGrid">
                    <div className="field">
                      <label>Левое поле (мм)</label>
                      <input
                        className="input"
                        type="number"
                        value={rules.margin_left_mm ?? 30}
                        onChange={(e) => updateRule("margin_left_mm", Number(e.target.value))}
                      />
                    </div>
                    <div className="field">
                      <label>Правое поле (мм)</label>
                      <input
                        className="input"
                        type="number"
                        value={rules.margin_right_mm ?? 15}
                        onChange={(e) => updateRule("margin_right_mm", Number(e.target.value))}
                      />
                    </div>
                    <div className="field">
                      <label>Верхнее поле (мм)</label>
                      <input
                        className="input"
                        type="number"
                        value={rules.margin_top_mm ?? 20}
                        onChange={(e) => updateRule("margin_top_mm", Number(e.target.value))}
                      />
                    </div>
                    <div className="field">
                      <label>Нижнее поле (мм)</label>
                      <input
                        className="input"
                        type="number"
                        value={rules.margin_bottom_mm ?? 20}
                        onChange={(e) => updateRule("margin_bottom_mm", Number(e.target.value))}
                      />
                    </div>
                  </div>

                  <div className="spacer" />

                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={!!rules.page_numbering}
                      onChange={(e) => updateRule("page_numbering", e.target.checked)}
                    />
                    Нумерация страниц
                  </label>

                  <div className="field" style={{ marginTop: 10 }}>
                    <label>Шрифт номера страницы (pt)</label>
                    <input
                      className="input"
                      type="number"
                      value={rules.page_number_font_size_pt ?? 12}
                      onChange={(e) => updateRule("page_number_font_size_pt", Number(e.target.value))}
                    />
                  </div>
                </div>

                <div className="card">
                  <details open>
                    <summary className="cardTitle" style={{ cursor: "pointer" }}>
                      Что нашлось автоматически
                    </summary>
                    <pre className="codebox codeboxScroll codeboxTight">
                      {JSON.stringify(rules.raw_matches ?? {}, null, 2)}
                    </pre>
                  </details>

                  <div className="spacer" />

                  <details>
                    <summary className="cardTitle" style={{ cursor: "pointer" }}>
                      Полный JSON
                    </summary>
                    <pre className="codebox">{JSON.stringify(rules, null, 2)}</pre>
                  </details>
                </div>
              </div>
            )}
          </div>
          {/* RIGHT */}
          <div>
            <div className="card">
              <div className="cardTitle">Профили</div>

              <div className="row">
                <input
                  className="input"
                  placeholder="Название профиля"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                />
                <button className="btn btnPrimary" onClick={saveCurrentAsProfile} disabled={!rules || loading}>
                  Сохранить
                </button>
              </div>

              <div className="spacer" />

              <div className="sideList">
                {profiles.length === 0 && <div className="small">Профилей пока нет.</div>}
                {profiles.map((p) => (
                  <div className="item" key={p.id}>
                    <div className="itemTitle">{p.name}</div>
                    <p className="itemMeta">Создан: {formatTs(p.created_at)}</p>
                    <div className="itemActions">
                      <button className="btn" onClick={() => applyRules(p.rules)} disabled={loading}>
                        Применить
                      </button>
                      <button className="btn btnDanger" onClick={() => deleteProfile(p.id)} disabled={loading}>
                        Удалить
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            <div className="card" style={{ marginTop: 14 }}>
              <div className="cardTitle">История шаблонов</div>

              <div className="sideList">
                {templates.length === 0 && <div className="small">Шаблоны пока не генерировались.</div>}
                {templates.map((t) => (
                  <div className="item" key={t.id}>
                    <div className="itemTitle">report_template.docx</div>
                    <p className="itemMeta">Дата: {formatTs(t.created_at)}</p>
                    <div className="itemActions">
                      <button
                        className="btn"
                        onClick={() => window.open(`${API}/api/download/${t.template_id}`, "_blank")}
                        disabled={loading}
                      >
                        Скачать снова
                      </button>
                      <button className="btn" onClick={() => applyRules(t.rules)} disabled={loading}>
                        Применить правила
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            </div>

            <div className="card" style={{ marginTop: 14 }}>
              <div className="cardTitle">История анализов</div>

              <div className="sideList">
                {history.length === 0 && <div className="small">История пока пустая.</div>}
                {history.map((h) => (
                  <div className="item" key={h.id}>
                    <div className="itemTitle">{h.filename}</div>
                    <p className="itemMeta">Дата: {formatTs(h.created_at)}</p>
                    <div className="itemActions">
                      <button className="btn" onClick={() => applyRules(h.rules)} disabled={loading}>
                        Применить правила
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="spacer" />
              <div className="small">Данные хранятся локально в backend/storage/ (json-файлы).</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
