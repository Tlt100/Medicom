import { ComingSoon } from '../../core/components/ComingSoon';
import { entryPath } from '../../core/paths';

export function BillCheck() {
  return (
    <ComingSoon
      path={entryPath('bill-check')}
      status="We’re building and testing the line-by-line comparison with synthetic bills and EOBs first."
      willDo={[
        'Read a provider’s bill and your insurer’s Explanation of Benefits (EOB), and line up the services they each list.',
        'Point out differences worth asking about, such as a charge that doesn’t appear on the EOB, or an amount you’re billed that is more than the EOB says you owe.',
        'Quote the exact line on each document for every difference it points out.',
      ]}
      wontDo={[
        'Decide that a bill is wrong or that anyone broke a rule. It shows differences and questions to ask.',
        'Store your bill or EOB, or show you prices without saying where they came from.',
      ]}
    />
  );
}
