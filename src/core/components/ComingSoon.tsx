import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { EntryPath } from '../paths';
import { Icon } from './Icon';

interface Props {
  path: EntryPath;
  /** What the finished tool will do, in plain terms. */
  willDo: string[];
  /** What it will deliberately not do. */
  wontDo: string[];
  /** Why it isn't available yet. */
  status: ReactNode;
}

/** Honest placeholder for a workflow that isn't built: no upload control, no sample results, nothing that looks like it works. */
export function ComingSoon({ path, willDo, wontDo, status }: Props) {
  return (
    <div className="container page narrow">
      <p className="eyebrow">Coming soon</p>
      <h1>{path.title}</h1>
      <p className="lede">{path.description}</p>

      <div className="callout callout-soon" role="note" aria-label="Not available yet">
        <Icon name="alert" size={22} className="callout-icon" />
        <div>
          <p className="callout-title">This isn’t available yet</p>
          <p>{status}</p>
          <p>Please don’t send us a bill for this yet. Nothing on this page accepts a file.</p>
        </div>
      </div>

      <h2>What it will do</h2>
      <ul>
        {willDo.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <h2>What it won’t do</h2>
      <ul>
        {wontDo.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <div className="hero-actions">
        <Link to="/" className="btn btn-secondary">
          Back to “What did you receive?”
        </Link>
        <Link to="/navigator" className="btn btn-quiet">
          I also have a denial letter
        </Link>
      </div>
    </div>
  );
}
