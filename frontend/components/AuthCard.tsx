export function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="auth-page">
      <div className="auth-hero">
        <div className="brand brand-lg">
          <span className="brand-mark">◆</span> AI Content Factory
        </div>
        <p className="auth-tagline">
          “Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST.”
        </p>
        <p className="muted">Research → Script → SEO → Video → Publish, fully automated by a multi-agent pipeline.</p>
      </div>
      <div className="auth-card card">
        <h1>{title}</h1>
        <p className="muted">{subtitle}</p>
        {children}
      </div>
    </div>
  );
}
