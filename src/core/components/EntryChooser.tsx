import { Link } from 'react-router-dom';
import { ENTRY_PATHS } from '../paths';
import { Icon } from './Icon';

/** "What did you receive?": the main way into the app. */
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
            <Link to={p.route} className="chooser-option" aria-labelledby={`chooser-${p.id}-title`} aria-describedby={`chooser-${p.id}-desc`}>
              <span className="chooser-icon" aria-hidden="true">
                <Icon name={p.icon} size={22} />
              </span>
              <span id={`chooser-${p.id}-title`} className="chooser-title">
                {p.title}
              </span>
              <span id={`chooser-${p.id}-desc`} className="chooser-desc">
                {p.description}
              </span>
              <Icon name="arrow" size={18} className="chooser-arrow" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
