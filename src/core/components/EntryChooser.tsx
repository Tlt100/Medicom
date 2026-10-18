import { Link } from 'react-router-dom';
import { ENTRY_PATHS } from '../paths';
import { Icon } from './Icon';

/** "What did you receive?": the main way into the app. Paths that aren't built yet say so before anyone clicks. */
export function EntryChooser({ headingLevel = 2 }: { headingLevel?: 2 | 3 }) {
  const Heading = `h${headingLevel}` as const;
  return (
    <section className="chooser" aria-labelledby="chooser-heading">
      <Heading id="chooser-heading" className="chooser-heading">
        What did you receive?
      </Heading>
      <ul className="chooser-list">
        {ENTRY_PATHS.map((p) => (
          <li key={p.id}>
            <Link to={p.route} className={p.ready ? 'chooser-option chooser-option-ready' : 'chooser-option chooser-option-soon'} aria-labelledby={p.ready ? `chooser-${p.id}-title` : `chooser-${p.id}-title chooser-${p.id}-status`}
              aria-describedby={`chooser-${p.id}-desc`}
            >
              <span className="chooser-title">
                <span id={`chooser-${p.id}-title`}>{p.title}</span>
                {p.ready ? (
                  <Icon name="arrow" size={18} />
                ) : (
                  <span id={`chooser-${p.id}-status`} className="badge badge-soon">
                    Coming soon
                  </span>
                )}
              </span>
              <span id={`chooser-${p.id}-desc`} className="chooser-desc">
                {p.description}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
