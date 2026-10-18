import { Route, Routes } from 'react-router-dom';
import { Layout } from './core/components/Layout';
import { About } from './pages/About';
import { Landing } from './pages/Landing';
import { BillCheck } from './features/bill-check/BillCheck';
import { Navigator } from './features/denials/Navigator';
import { Uninsured } from './features/uninsured/Uninsured';
import { NotFound } from './pages/NotFound';
import { Sources } from './pages/Sources';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="navigator" element={<Navigator />} />
        <Route path="bill-check" element={<BillCheck />} />
        <Route path="uninsured" element={<Uninsured />} />
        <Route path="sources" element={<Sources />} />
        <Route path="about" element={<About />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
