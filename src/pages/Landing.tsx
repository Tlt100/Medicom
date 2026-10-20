import { Link } from 'react-router-dom';
import { EntryChooser } from '../core/components/EntryChooser';
import { Icon, type IconName } from '../core/components/Icon';

const PROMISES: { icon: IconName; text: string }[] = [
  { icon: 'doc', text: 'Every detail linked to your document' },
  { icon: 'scale', text: 'Every rule linked to an official source' },
  { icon: 'lock', text: 'Nothing stored, no account' },
];

export function Landing() {
  return (
    <section className="hero hero-simple">
      <div className="container">
        <p className="eyebrow">New Jersey</p>
        <h1>Make sense of a denial or a medical bill.</h1>
        <p className="lede">Pick what you got. We’ll show what it says and which rules may apply.</p>

        <EntryChooser />

        <p className="hero-links">
          <Link to="/prices" className="text-link">
            Compare a price with Medicare <Icon name="arrow" size={16} />
          </Link>
          <Link to="/sources" className="text-link">
            Browse the sources <Icon name="arrow" size={16} />
          </Link>
        </p>

        <ul className="promises">
          {PROMISES.map((p) => (
            <li key={p.text}>
              <Icon name={p.icon} size={18} /> {p.text}
            </li>
          ))}
        </ul>
        <p className="fine-print">
          Educational, not legal advice. Urgent care? Call your insurer and ask for an expedited appeal. Emergencies: 911.{' '}
          <Link to="/about">Scope and limits</Link>
        </p>
      </div>
    </section>
  );
}
