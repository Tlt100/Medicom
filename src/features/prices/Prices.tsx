import { Link } from 'react-router-dom';
import { PriceContext } from '../../core/components/PriceContext';

export function Prices() {
  return (
    <div className="container page">
      <p className="eyebrow">Price context</p>
      <h1>How does a charge compare with Medicare?</h1>
      <p className="lede">
        For common services, see what Medicare pays in New Jersey, and compare it with the charge on your bill and the hospital’s own published
        price. It’s context for a question, not a verdict.
      </p>
      <PriceContext title="Common services" headingLevel={2} />
      <p>
        Have a bill and an EOB? <Link to="/bill-check">Compare them line by line</Link>. Uninsured?{' '}
        <Link to="/uninsured">See what you may be eligible for</Link>.
      </p>
    </div>
  );
}
