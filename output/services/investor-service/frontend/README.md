# investor

Frontend for investor

> Generated: 2026-03-10T13:09:13.176583Z
> Generator: codegen-os v1.0.0

## Tech Stack

| Category | Technology | Version |
|----------|------------|---------|
| Framework | React | 18.x |
| Language | TypeScript | 5.x |
| Build Tool | Vite | 6.x |
| UI Library | Material UI | 7.x |
| Data Fetching | React Query | 5.x |
| Routing | React Router | 7.x |
| Forms | React Hook Form + Zod | 7.x + 3.x |
| HTTP Client | Axios | 1.x |

## Quick Start

### Prerequisites

- Node.js 18.0.0 or higher
- npm 9.0.0 or higher
- Backend API running at `http://localhost:8060`

### Installation

```bash
# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env.local

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173`.

### Backend Setup

Ensure your backend API is running. The frontend expects the API at:
- **Base URL**: `http://localhost:8060`
- **API Prefix**: `/api`

Update `.env.local` if your backend runs on a different URL:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_PATH_PREFIX=/api
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build for production (TypeScript check + Vite build) |
| `npm run preview` | Preview production build locally |
| `npm run typecheck` | Run TypeScript type checking |
| `npm run lint` | Run ESLint on source files |
| `npm run lint:fix` | Run ESLint and fix auto-fixable issues |
| `npm run format` | Format code with Prettier |
| `npm run format:check` | Check code formatting |
| `npm run test` | Run tests once |
| `npm run test:watch` | Run tests in watch mode |
| `npm run test:coverage` | Run tests with coverage report |
| `npm run clean` | Remove build artifacts and cache |

## Project Structure

```
investor/
├── public/                 # Static assets
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── InvestorList.tsx
│   │   ├── InvestorDetail.tsx
│   │   ├── InvestorForm.tsx
│   │   └── FormInvestorSelect.tsx
│   │   ├── InvestorEmailList.tsx
│   │   ├── InvestorEmailDetail.tsx
│   │   ├── InvestorEmailForm.tsx
│   │   └── FormInvestorEmailSelect.tsx
│   │   ├── InvestorMarketList.tsx
│   │   ├── InvestorMarketDetail.tsx
│   │   ├── InvestorMarketForm.tsx
│   │   └── FormInvestorMarketSelect.tsx
│   │   ├── InvestorPastInvestmentList.tsx
│   │   ├── InvestorPastInvestmentDetail.tsx
│   │   ├── InvestorPastInvestmentForm.tsx
│   │   └── FormInvestorPastInvestmentSelect.tsx
│   │   ├── MarketList.tsx
│   │   ├── MarketDetail.tsx
│   │   ├── MarketForm.tsx
│   │   └── FormMarketSelect.tsx
│   │   ├── PastInvestmentList.tsx
│   │   ├── PastInvestmentDetail.tsx
│   │   ├── PastInvestmentForm.tsx
│   │   └── FormPastInvestmentSelect.tsx
│   ├── hooks/              # Custom React hooks
│   │   ├── useInvestors.ts
│   │   ├── useInvestorEmails.ts
│   │   ├── useInvestorMarkets.ts
│   │   ├── useInvestorPastInvestments.ts
│   │   ├── useMarkets.ts
│   │   ├── usePastInvestments.ts
│   │   └── queryKeys.ts    # React Query cache keys
│   ├── services/           # API service functions
│   │   ├── investorService.ts
│   │   ├── investorEmailService.ts
│   │   ├── investorMarketService.ts
│   │   ├── investorPastInvestmentService.ts
│   │   ├── marketService.ts
│   │   ├── pastInvestmentService.ts
│   ├── types/              # TypeScript type definitions
│   │   ├── investor.types.ts
│   │   ├── investorEmail.types.ts
│   │   ├── investorMarket.types.ts
│   │   ├── investorPastInvestment.types.ts
│   │   ├── market.types.ts
│   │   ├── pastInvestment.types.ts
│   ├── pages/              # Route page components
│   │   ├── Home.tsx
│   │   ├── InvestorPage.tsx
│   │   ├── InvestorEmailPage.tsx
│   │   ├── InvestorMarketPage.tsx
│   │   ├── InvestorPastInvestmentPage.tsx
│   │   ├── MarketPage.tsx
│   │   ├── PastInvestmentPage.tsx
│   │   └── NotFound.tsx
│   ├── layouts/            # Layout components
│   │   └── Layout.tsx
│   ├── App.tsx             # Root application component
│   ├── main.tsx            # Application entry point
│   └── router.tsx          # Route configuration
├── .env.example            # Environment variables template
├── index.html              # HTML entry point
├── package.json            # Project dependencies
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite build configuration
└── README.md               # This file
```

## Entities

This application manages the following entities:

| Entity | API Endpoint | Route |
|--------|--------------|-------|
| Investor | `/api/investors` | `/investors` |
| InvestorEmail | `/api/investor-emails` | `/investor-emails` |
| InvestorMarket | `/api/investor-markets` | `/investor-markets` |
| InvestorPastInvestment | `/api/investor-past-investments` | `/investor-past-investments` |
| Market | `/api/markets` | `/markets` |
| PastInvestment | `/api/past-investments` | `/past-investments` |

## Development Guide

### Adding a New Entity

1. **Define the entity schema** in your backend
2. **Run the generator** to create frontend components:
   ```bash
   codegen generate -i entities/new_entity.yaml -o . --language typescript
   ```
3. **Update the router** in `src/router.tsx` to include the new route
4. **Add navigation** in `src/layouts/Layout.tsx` for the new entity

### Using React Query

All data fetching uses React Query for caching, background updates, and optimistic mutations.

**Fetching data:**
```tsx
import { useInvestors } from '../hooks/useInvestors';

function MyComponent() {
  const { data, isLoading, error } = useInvestors();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <div>{data?.map(item => <div key={item.id}>{item.name}</div>)}</div>;
}
```

**Mutations (Create/Update/Delete):**
```tsx
import { useCreateInvestor, useUpdateInvestor, useDeleteInvestor } from '../hooks/useInvestors';

function MyComponent() {
  const createMutation = useCreateInvestor();
  const updateMutation = useUpdateInvestor();
  const deleteMutation = useDeleteInvestor();

  const handleCreate = () => {
    createMutation.mutate({ name: 'New Item' });
  };

  const handleUpdate = (id: string) => {
    updateMutation.mutate({ id, data: { name: 'Updated' } });
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };
}
```

### React Query DevTools

React Query DevTools are enabled by default in development. Toggle the panel by clicking the React Query logo in the bottom-right corner.

To disable DevTools, set in `.env.local`:
```env
VITE_ENABLE_DEVTOOLS=false
```

### Forms and Validation

Forms use React Hook Form with Zod for schema validation:

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
});

type FormData = z.infer<typeof schema>;

function MyForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <span>{errors.name.message}</span>}
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      <button type="submit">Submit</button>
    </form>
  );
}
```

### Customizing the Theme

The Material UI theme can be customized in `src/App.tsx` or by creating a separate `src/theme.ts` file:

```tsx
import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: 'Inter, sans-serif',
  },
});
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8060` |
| `VITE_API_PATH_PREFIX` | API path prefix | `/api` |
| `VITE_API_TIMEOUT` | API request timeout (ms) | `30000` |
| `VITE_APP_NAME` | Application name | `investor` |
| `VITE_LOG_LEVEL` | Log level (debug/info/warn/error) | `info` |
| `VITE_ENABLE_DEVTOOLS` | Enable React Query DevTools | `true` |
| `VITE_ENABLE_MOCKS` | Enable Mock Service Worker | `false` |

## Production Build

```bash
# Build for production
npm run build

# Preview the build locally
npm run preview
```

The build output will be in the `dist/` directory. Deploy this directory to your static hosting provider.

### Build Optimization

The production build includes:
- TypeScript type checking
- Tree shaking for unused code
- Code splitting for routes (lazy loading)
- Asset optimization and minification
- Source maps (configurable)

## Testing

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

Tests use Vitest with React Testing Library. Place test files next to components:

```
src/
├── components/
│   ├── MyComponent.tsx
│   └── MyComponent.test.tsx
```

## Troubleshooting

### API Connection Issues

1. Verify the backend is running
2. Check `VITE_API_BASE_URL` in `.env.local`
3. Ensure CORS is configured on the backend
4. Check browser console for network errors

### Build Errors

1. Run `npm run typecheck` to find type errors
2. Run `npm run lint` to find linting issues
3. Clear cache with `npm run clean` and rebuild

### Hot Reload Not Working

1. Check if the dev server is running (`npm run dev`)
2. Clear browser cache
3. Restart the dev server

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests: `npm run test`
4. Run linting: `npm run lint`
5. Run type check: `npm run typecheck`
6. Submit a pull request

## License

This project is licensed under the MIT License.
