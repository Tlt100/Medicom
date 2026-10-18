import { ComingSoon } from '../../core/components/ComingSoon';
import { entryPath } from '../../core/paths';

export function Uninsured() {
  return (
    <ComingSoon
      path={entryPath('uninsured')}
      status="We’re checking New Jersey’s rules for uninsured patients and the federal poverty guidelines against official sources before building this."
      willDo={[
        'Ask a few questions, such as household size and income, to see whether you may be eligible for New Jersey’s limits on what hospitals can charge some uninsured patients.',
        'Show the rule it relies on, with a link to the official source and the date it was checked.',
        'Explain what to ask the hospital for, and in what order.',
      ]}
      wontDo={[
        'Tell you that you were illegally billed, or guarantee that a hospital will reduce a bill. Only the hospital, a regulator or a court can decide that.',
        'Store your income or household details.',
      ]}
    />
  );
}
