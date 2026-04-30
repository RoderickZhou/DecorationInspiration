function StatCard({ label, value, desc }) {
  return (
    <div className="stat">
      <div className="subtle">{label}</div>
      <strong>{value}</strong>
      <div className="subtle">{desc}</div>
    </div>
  );
}

export default StatCard;
