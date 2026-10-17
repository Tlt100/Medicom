import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="container page narrow">
      <h1>Page not found</h1>
      <p className="lede">We couldn’t find that page.</p>
      <Link to="/" className="btn btn-primary">
        Go to the home page
      </Link>
    </div>
  );
}
