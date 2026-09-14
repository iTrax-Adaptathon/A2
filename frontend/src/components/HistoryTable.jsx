import { useState } from "react";
import { deleteLog } from "../api";

function SourceDot({ source }) {
  return <span className={`source-dot source-dot-${source}`} title={source} />;
}

export default function HistoryTable({ trend, onChanged }) {
  const [deletingDate, setDeletingDate] = useState(null);

  if (!trend?.length) return null;

  async function handleDelete(date) {
    setDeletingDate(date);
    try {
      await deleteLog(date);
      onChanged();
    } finally {
      setDeletingDate(null);
    }
  }

  const rows = [...trend].reverse(); // most recent first

  return (
    <div className="card">
      <h2>Logged days</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Commute</th>
              <th>Food</th>
              <th>Energy</th>
              <th>Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((entry) => (
              <tr key={entry.date}>
                <td>{entry.date}</td>
                <td>
                  {entry.commute.kg_co2e} kg <SourceDot source={entry.commute.source} />
                </td>
                <td>
                  {entry.food.kg_co2e} kg <SourceDot source={entry.food.source} />
                </td>
                <td>
                  {entry.energy.kg_co2e} kg <SourceDot source={entry.energy.source} />
                </td>
                <td>
                  <strong>{entry.total_kg_co2e} kg</strong>
                </td>
                <td>
                  <button
                    className="link-button"
                    onClick={() => handleDelete(entry.date)}
                    disabled={deletingDate === entry.date}
                  >
                    {deletingDate === entry.date ? "..." : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint">
        <SourceDot source="logged" /> logged &nbsp;
        <SourceDot source="estimated" /> estimated from your average &nbsp;
        <SourceDot source="default" /> population default (no history yet)
      </p>
    </div>
  );
}
