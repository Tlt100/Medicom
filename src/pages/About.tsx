import { Link } from 'react-router-dom';

export function About() {
  return (
    <div className="container page narrow">
      <p className="eyebrow">About & limits</p>
      <h1>What Medicom is, and what it isn’t</h1>
      <p className="lede">
        Medicom helps people understand a health insurance denial: what the letter actually says, which rules apply to their plan,
        and what the verified next steps are.
      </p>

      <h2>Scope</h2>
      <ul>
        <li>New Jersey residents and applicable U.S. federal law.</li>
        <li>Denials of coverage or payment by a health plan. Medical bills checked against an insurer’s Explanation of Benefits. Hospital bills for uninsured New Jersey patients: whether Charity Care or the state’s limit on charges may apply (an estimate, not a decision).</li>
        <li>
          Plan types it distinguishes: NJ state-regulated (fully insured), self-funded employer (ERISA), ACA marketplace (Get Covered New
          Jersey), NJ FamilyCare / Medicaid, Medicare / Medicare Advantage, and “not sure.”
        </li>
      </ul>

      <h2>Limits</h2>
      <ul>
        <li>It is an educational navigation tool, not a law firm, insurer, medical provider, or government service.</li>
        <li>It does not give legal advice or medical advice, and it never predicts or guarantees an appeal outcome.</li>
        <li>It does not decide whether a law was violated. Only a regulator or a court can.</li>
        <li>
          Deadlines it shows are general rules from official sources. Your plan documents and letters control. When in doubt, act early and
          confirm in writing.
        </li>
        <li>Medicare and Medicaid have their own appeal systems; Medicom points you to them but does not cover every level.</li>
      </ul>

      <h2>Urgent situations</h2>
      <p>
        If waiting could seriously harm your health, contact your insurer right away and ask for an expedited (urgent) appeal, and ask your
        doctor to support the request. For a medical emergency, call 911.
      </p>

      <h2>Your data</h2>
      <ul>
        <li>This is a portfolio prototype. Use the synthetic samples. It is not approved for real protected health information.</li>
        <li>No account and no database. Uploaded letters are processed in memory for a single request and not stored or logged.</li>
        <li>Medicom does not claim HIPAA compliance or certification.</li>
      </ul>

      <h2>How sources work</h2>
      <p>
        Every legal statement cites an entry in the <Link to="/sources">source library</Link>. Each entry records the issuing authority,
        whether it is binding law, agency guidance, or educational material, the date we last checked it, and a verbatim excerpt. Anything we
        couldn’t confirm is flagged for human review.
      </p>
    </div>
  );
}
