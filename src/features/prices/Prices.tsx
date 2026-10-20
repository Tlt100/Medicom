import { Link } from 'react-router-dom';
import { PriceContext } from '../../core/components/PriceContext';

export function Prices() {
  return (
    <div className="container page">
      <p className="eyebrow">Price context</p>
      <h1>How does a charge compare with Medicare?</h1>
      <p className="lede">What Medicare pays in New Jersey for common services, next to your charge.</p>
      <PriceContext title="Common services" headingLevel={2} />
      <p>
        Have a bill and an EOB? <Link to="/bill-check">Compare them line by line</Link>. Uninsured?{' '}
        <Link to="/uninsured">See what you may be eligible for</Link>.
      </p>
    </div>
  );
}
