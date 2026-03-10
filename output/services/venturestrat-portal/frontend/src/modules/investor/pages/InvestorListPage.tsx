import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Pagination from '@mui/material/Pagination';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import { Search } from 'lucide-react';
import InvestorSearchBar, { type SearchFilters } from '../components/InvestorSearchBar';
import InvestorCard from '../components/InvestorCard';
import { useInvestorSearch } from '../hooks/useInvestorSearch';
import { useSubscriptionStatus } from '../hooks/useSubscriptionStatus';
import { useQuery } from '@tanstack/react-query';
import { crmApi } from '@modules/crm/api/crmApi';

const PAGE_SIZE_OPTIONS = [20, 50, 100];
const DEFAULT_PAGE_SIZE = 20;

const EMPTY_FILTERS: SearchFilters = {
  q: '',
  location: [],
  stages: [],
  types: [],
  markets: [],
};

const InvestorListPage: React.FC = () => {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<SearchFilters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  // Track IDs shortlisted in this session (in addition to server-fetched set)
  const [locallyShortlisted, setLocallyShortlisted] = useState<Set<string>>(new Set());

  const { data: subStatus } = useSubscriptionStatus();

  const { data, isLoading, isError, error } = useInvestorSearch({
    q: filters.q || undefined,
    location: filters.location.length > 0 ? filters.location : undefined,
    stages: filters.stages.length > 0 ? filters.stages : undefined,
    types: filters.types.length > 0 ? filters.types : undefined,
    markets: filters.markets.length > 0 ? filters.markets : undefined,
    page,
    page_size: pageSize,
  });

  // Fetch existing shortlists to know which investors are already in the pipeline
  const { data: shortlists } = useQuery({
    queryKey: ['crm', 'shortlists-for-discover'],
    queryFn: () => crmApi.getShortlists(),
    staleTime: 2 * 60 * 1000,
  });

  // Fetch pipeline stages to get the first stage ID for new shortlists
  const { data: pipelineStages } = useQuery({
    queryKey: ['crm', 'pipeline-stages-for-discover'],
    queryFn: () => crmApi.getPipelineStages(),
    staleTime: 30 * 60 * 1000,
  });

  const shortlistedIds = useMemo(() => {
    const ids = new Set<string>(shortlists?.map((sl) => sl.investor_id) ?? []);
    // Merge locally shortlisted IDs (for optimistic UI before next query refresh)
    locallyShortlisted.forEach((id) => ids.add(id));
    return ids;
  }, [shortlists, locallyShortlisted]);

  const firstStageId = useMemo(() => {
    if (!pipelineStages || pipelineStages.length === 0) return null;
    const sorted = [...pipelineStages].sort((a, b) => a.sequence - b.sequence);
    return sorted[0]?.id ?? null;
  }, [pipelineStages]);

  const handleFiltersChange = useCallback((newFilters: SearchFilters) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  const handleShortlisted = useCallback((investorId: string) => {
    setLocallyShortlisted((prev) => new Set([...prev, investorId]));
  }, []);

  const handlePageSizeChange = useCallback((newSize: number) => {
    setPageSize(newSize);
    setPage(1);
  }, []);

  const items = data?.items ?? [];
  const totalPages = data?.pagination?.total_pages ?? 1;
  const totalCount = data?.pagination?.total ?? 0;

  return (
    <Box sx={{ px: 3, py: 2, maxWidth: 1400, mx: 'auto' }}>
      {/* Breadcrumb */}
      <Breadcrumbs sx={{ mb: 1.5, fontSize: 13 }}>
        <Link
          underline="hover"
          color="#6b7280"
          sx={{ cursor: 'pointer', fontSize: 13 }}
          onClick={() => navigate('/')}
        >
          Home
        </Link>
        <Link
          underline="hover"
          color="#6b7280"
          sx={{ cursor: 'pointer', fontSize: 13 }}
          onClick={() => {}}
        >
          Fundraising
        </Link>
        <Typography color="#374151" sx={{ fontSize: 13 }}>
          Investors
        </Typography>
      </Breadcrumbs>

      {/* Title row with Profiles selector and Search */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography
          variant="h5"
          sx={{ fontWeight: 700, color: '#1a1a1a' }}
        >
          Investor Directory
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ color: '#6b7280', fontSize: 13 }}>
              Profiles:
            </Typography>
            <Select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              size="small"
              sx={{
                minWidth: 100,
                height: 32,
                fontSize: 13,
                bgcolor: '#ffffff',
                '& .MuiSelect-select': { py: 0.5 },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: '#d1d5db' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#9ca3af' },
              }}
            >
              {PAGE_SIZE_OPTIONS.map((opt) => (
                <MenuItem key={opt} value={opt}>
                  {opt} Per Page
                </MenuItem>
              ))}
            </Select>
          </Box>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.75,
              px: 1.5,
              py: 0.5,
              border: '1px solid #d1d5db',
              borderRadius: 1,
              bgcolor: '#ffffff',
              cursor: 'text',
              minWidth: 140,
            }}
            onClick={() => {
              // Focus the search bar below
              const el = document.querySelector<HTMLInputElement>('[placeholder*="Search by name"]');
              if (el) el.focus();
            }}
          >
            <Search size={16} color="#9ca3af" />
            <Typography sx={{ fontSize: 13, color: '#9ca3af' }}>Search</Typography>
          </Box>
        </Box>
      </Box>

      <InvestorSearchBar filters={filters} onFiltersChange={handleFiltersChange} />

      <Typography variant="body2" sx={{ color: '#6b7280', mt: 1.5, mb: 1 }}>
        {isLoading
          ? 'Searching...'
          : `${totalCount.toLocaleString()} investor${totalCount === 1 ? '' : 's'} found`}
      </Typography>

      {isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {(error as Error)?.message ?? 'Failed to load investors.'}
        </Alert>
      )}

      {isLoading ? (
        <Stack spacing={1.5}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton
              key={i}
              variant="rounded"
              height={100}
              sx={{ borderRadius: 2 }}
            />
          ))}
        </Stack>
      ) : items.length === 0 ? (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            py: 8,
          }}
        >
          <Search size={48} color="#999999" />
          <Typography
            variant="h6"
            sx={{ color: '#888888', mt: 2, fontWeight: 500 }}
          >
            No investors found
          </Typography>
          <Typography variant="body2" sx={{ color: '#999999', mt: 0.5 }}>
            Try adjusting your search or filters.
          </Typography>
        </Box>
      ) : (
        <Stack spacing={1.5}>
          {items.map((investor) => (
            <InvestorCard
              key={investor.id}
              investor={investor}
              hasSubscription={subStatus?.hasActiveSubscription ?? false}
              shortlistedIds={shortlistedIds}
              firstStageId={firstStageId}
              onShortlisted={handleShortlisted}
            />
          ))}
        </Stack>
      )}

      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, mb: 2 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, p) => setPage(p)}
            shape="rounded"
            sx={{
              '& .MuiPaginationItem-root': {
                color: '#666666',
                borderColor: '#e0e0e0',
                '&.Mui-selected': {
                  bgcolor: '#1976d2',
                  color: '#ffffff',
                  '&:hover': { bgcolor: '#1565c0' },
                },
                '&:hover': { bgcolor: '#f5f5f5' },
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
};

export default InvestorListPage;
