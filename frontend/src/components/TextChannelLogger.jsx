import { useRef, useState } from "react";
import { parseLogText, upsertLog } from "../api";
import SourceBadge from "./SourceBadge";

const PLACEHOLDERS = {
  natural_language:
    "e.g. \"Drove 14km to work, had a vegetarian lunch, used about 6 kwh\" or \"Took the train yesterday, mostly meat meals\"",
  voice: "Press the mic and describe your day — it'll be transcribed here.",
  receipt: "Upload a fuel, electricity, or grocery receipt photo — extracted text will appear here.",
};

const SpeechRecognitionAPI =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export default function TextChannelLogger({ channel, region, onSaved }) {
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [listening, setListening] = useState(false);
  const [ocrRunning, setOcrRunning] = useState(false);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [imagePreview, setImagePreview] = useState(null);
  const recognitionRef = useRef(null);

  async function handleParse(rawText = text) {
    if (!rawText.trim()) return;
    setParsing(true);
    setError(null);
    try {
      const result = await parseLogText(rawText, channel, region);
      setParsed(result);
    } catch {
      setError("Couldn't parse that text.");
    } finally {
      setParsing(false);
    }
  }

  async function handleSave() {
    if (!parsed) return;
    setSaving(true);
    setError(null);
    try {
      await upsertLog({
        date: parsed.date,
        commute_mode: parsed.commute_mode,
        commute_distance_km: parsed.commute_distance_km,
        diet_type: parsed.diet_type,
        energy_kwh: parsed.energy_kwh,
        energy_level: parsed.energy_level,
        notes: parsed.raw_text,
        region,
        channel,
        inferred_fields: parsed.inferred_fields,
      });
      onSaved();
      setText("");
      setParsed(null);
      setImagePreview(null);
    } catch (err) {
      setError(err?.response?.data?.detail ? JSON.stringify(err.response.data.detail) : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  function startListening() {
    if (!SpeechRecognitionAPI) return;
    const recognition = new SpeechRecognitionAPI();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;
    let finalTranscript = "";
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += t + " ";
        else interim += t;
      }
      setText((finalTranscript + interim).trim());
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setListening(false);
  }

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImagePreview(URL.createObjectURL(file));
    setOcrRunning(true);
    setOcrProgress(0);
    setError(null);
    try {
      const Tesseract = (await import("tesseract.js")).default;
      const { data } = await Tesseract.recognize(file, "eng", {
        logger: (m) => {
          if (m.status === "recognizing text") setOcrProgress(Math.round(m.progress * 100));
        },
      });
      setText(data.text.trim());
    } catch {
      setError("OCR failed to read that image. Try a clearer photo, or type the details instead.");
    } finally {
      setOcrRunning(false);
    }
  }

  const parsedFields = parsed
    ? [
        {
          label: "Commute",
          value: parsed.commute_mode ? `${parsed.commute_mode}, ${parsed.commute_distance_km}km` : null,
          inferred: parsed.inferred_fields.includes("commute"),
        },
        {
          label: "Food",
          value: parsed.diet_type,
          inferred: parsed.inferred_fields.includes("food"),
        },
        {
          label: "Energy",
          value: parsed.energy_kwh != null ? `${parsed.energy_kwh} kWh` : parsed.energy_level,
          inferred: parsed.inferred_fields.includes("energy"),
        },
      ]
    : [];

  return (
    <div className="channel-logger">
      {channel === "voice" && (
        <div className="voice-controls">
          {SpeechRecognitionAPI ? (
            <button
              type="button"
              className={`mic-button ${listening ? "listening" : ""}`}
              onClick={listening ? stopListening : startListening}
            >
              {listening ? "Stop listening" : "Start speaking"}
            </button>
          ) : (
            <p className="hint">
              Voice input needs the Web Speech API (Chrome or Edge). Type your day below instead.
            </p>
          )}
        </div>
      )}

      {channel === "receipt" && (
        <div className="receipt-controls">
          <label className="file-drop">
            <input type="file" accept="image/*" onChange={handleFile} hidden />
            {imagePreview ? <img src={imagePreview} alt="Receipt preview" /> : <span>Choose a receipt photo</span>}
          </label>
          {ocrRunning && (
            <div className="ocr-progress">
              <div className="ocr-progress-bar" style={{ width: `${ocrProgress}%` }} />
              <span>Reading receipt&hellip; {ocrProgress}%</span>
            </div>
          )}
        </div>
      )}

      <textarea
        className="channel-textarea"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={PLACEHOLDERS[channel]}
        rows={channel === "receipt" ? 4 : 3}
      />

      <button type="button" onClick={() => handleParse()} disabled={!text.trim() || parsing}>
        {parsing ? "Parsing..." : "Detect footprint"}
      </button>

      {error && <p className="error">{error}</p>}

      {parsed && (
        <div className="parse-preview">
          <div className="parse-preview-header">
            <strong>Detected for {parsed.date}</strong>
          </div>
          <ul className="parse-fields">
            {parsedFields.map((f) => (
              <li key={f.label}>
                <span className="parse-field-label">{f.label}</span>
                {f.value ? (
                  <>
                    <span className="parse-field-value">{f.value}</span>
                    <SourceBadge source={f.inferred ? "inferred" : "observed"} />
                  </>
                ) : (
                  <span className="parse-field-value muted">not mentioned</span>
                )}
              </li>
            ))}
          </ul>
          {parsed.explanations.length > 0 && (
            <ul className="parse-explanations">
              {parsed.explanations.map((ex, i) => (
                <li key={i}>{ex}</li>
              ))}
            </ul>
          )}
          <div className="parse-actions">
            <button type="button" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save this day"}
            </button>
            <button type="button" className="secondary" onClick={() => setParsed(null)}>
              Edit text
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
