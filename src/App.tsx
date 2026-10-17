import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { About } from './pages/About';
import { InDevelopment } from './pages/InDevelopment';
import { Landing } from './pages/Landing';
import { NotFound } from './pages/NotFound';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route
          path="navigator"
          element={
            <InDevelopment
              title="Denial Navigator"
              description="Upload a synthetic denial letter, see each detail linked to its page and passage, identify your plan type, and get a cited checklist."
              milestone="milestones 2–4"
            />
          }
        />
        <Route
          path="sources"
          element={
            <InDevelopment
              title="Source library"
              description="Browse every official source PatientShield relies on, with its authority, legal weight, dates, verbatim excerpts, and review status."
              milestone="milestone 5"
            />
          }
        />
        <Route path="about" element={<About />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
