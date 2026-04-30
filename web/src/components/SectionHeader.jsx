function SectionHeader({ title, description, pill }) {
  return (
    <div className="section-head">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {pill ? <div className="pill">{pill}</div> : null}
    </div>
  );
}

export default SectionHeader;
