import { useState } from "react";
import { deleteLog } from "../api";
import SourceBadge from "./SourceBadge";

const CHANNEL_LABEL = {
  form: "Form",
  natural_language: "Text",
  voice: "Voice",
  receipt: "Receipt",
};

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
              <th>Via</th>
              <th>Commute</th>
              <th>Food</th>
              <th>Energy</th>
              <th>Flights</th>
              <th>Shopping</th>
              <th>Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((entry) => (
              <tr key={entry.date}>
                <td>{entry.date}</td>
                <td>
                  <span className="channel-pill">{CHANNEL_LABEL[entry.channel] || entry.channel}</span>
                </td>
                <td>
                  {entry.commute.kg_co2e} kg <SourceBadge source={entry.commute.source} />
                </td>
                <td>
                  {entry.food.kg_co2e} kg <SourceBadge source={entry.food.source} />
                </td>
                <td>
                  {entry.energy.kg_co2e} kg <SourceBadge source={entry.energy.source} />
                </td>
                <td>
                  {entry.flights.kg_co2e > 0 ? (
                    <>
                      {entry.flights.kg_co2e} kg <SourceBadge source={entry.flights.source} />
                    </>
                  ) : (
                    <span className="muted">&mdash;</span>
                  )}
                </td>
                <td>
                  {entry.shopping.kg_co2e} kg <SourceBadge source={entry.shopping.source} />
                </td>
                <td>
                  <strong>{entry.total_kg_co2e} kg</strong>
                  <span className="muted"> ({entry.total_low_kg_co2e}&ndash;{entry.total_high_kg_co2e})</span>
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
    </div>
  );
}
