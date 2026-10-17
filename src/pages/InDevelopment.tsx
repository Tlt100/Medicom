import { Link } from 'react-router-dom';
import { Icon } from '../components/Icon';

interface Props {
  title: string;
  description: string;
  milestone: string;
}

/** Honest placeholder for routes that are planned but not built yet. No fake controls. */
export function InDevelopment({ title, description, milestone }: Props) {
  return (
    <div className="container page narrow">
      <h1>{title}</h1>
      <div className="empty-state">
        <Icon name="route" size={28} className="empty-icon" />
        <h2>In development</h2>
        <p>{description}</p>
        <p className="muted">Planned for {milestone}.</p>
        <Link to="/" className="btn btn-secondary">
          Back to home
        </Link>
      </div>
    </div>
  );
}
