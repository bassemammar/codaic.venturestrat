import React, { useState, useCallback, useEffect, useRef } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select, { type SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Checkbox from '@mui/material/Checkbox';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import OutlinedInput from '@mui/material/OutlinedInput';
import CircularProgress from '@mui/material/CircularProgress';
import { Search, X, Users, Target, TrendingUp, Globe, MapPin, Map } from 'lucide-react';
import { Country, State, City } from 'country-state-city';
import { useInvestorFilters } from '../hooks/useInvestorFilters';

export interface SearchFilters {
  q: string;
  location: string[];
  stages: string[];
  types: string[];
  markets: string[];
}

interface InvestorSearchBarProps {
  filters: SearchFilters;
  onFiltersChange: (filters: SearchFilters) => void;
}

const DEBOUNCE_MS = 300;

const pillSelectSx = {
  bgcolor: '#ffffff',
  borderRadius: '20px',
  '& .MuiOutlinedInput-notchedOutline': {
    borderColor: '#d1d5db',
    borderRadius: '20px',
  },
  '&:hover .MuiOutlinedInput-notchedOutline': {
    borderColor: '#9ca3af',
  },
  '& .MuiSelect-select': {
    color: '#374151',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    py: '6px',
    pl: '12px',
    pr: '28px !important',
    fontSize: 13,
  },
};

const menuPropsSx = {
  PaperProps: {
    sx: {
      bgcolor: '#ffffff',
      border: '1px solid #e5e7eb',
      maxHeight: 300,
    },
  },
};

const ALL_COUNTRIES = Country.getAllCountries();

const InvestorSearchBar: React.FC<InvestorSearchBarProps> = ({
  filters,
  onFiltersChange,
}) => {
  const { data: filterOptions, isLoading: filtersLoading } = useInvestorFilters();
  const [localQuery, setLocalQuery] = useState(filters.q);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cascading location state — stored as ISO codes internally, names sent to API
  const [selectedCountryCode, setSelectedCountryCode] = useState('');
  const [selectedStateCode, setSelectedStateCode] = useState('');
  const [selectedCityName, setSelectedCityName] = useState('');

  const stateOptions = selectedCountryCode
    ? State.getStatesOfCountry(selectedCountryCode)
    : [];

  const cityOptions =
    selectedCountryCode && selectedStateCode
      ? City.getCitiesOfState(selectedCountryCode, selectedStateCode)
      : [];

  // Sync external filter.q changes into local state
  useEffect(() => {
    setLocalQuery(filters.q);
  }, [filters.q]);

  // Build the location array from cascading selections and emit upstream
  const emitLocationChange = useCallback(
    (
      countryCode: string,
      stateCode: string,
      cityName: string,
      currentFilters: SearchFilters,
    ) => {
      const countryName = countryCode
        ? (Country.getCountryByCode(countryCode)?.name ?? '')
        : '';
      const stateName =
        countryCode && stateCode
          ? (State.getStateByCodeAndCountry(stateCode, countryCode)?.name ?? '')
          : '';

      // Build location array: most specific to least specific, filter empty
      const location = [cityName, stateName, countryName].filter(Boolean);
      onFiltersChange({ ...currentFilters, location });
    },
    [onFiltersChange],
  );

  const handleCountryChange = (e: SelectChangeEvent<string>) => {
    const code = e.target.value;
    setSelectedCountryCode(code);
    setSelectedStateCode('');
    setSelectedCityName('');
    emitLocationChange(code, '', '', { ...filters, q: localQuery });
  };

  const handleStateChange = (e: SelectChangeEvent<string>) => {
    const code = e.target.value;
    setSelectedStateCode(code);
    setSelectedCityName('');
    emitLocationChange(selectedCountryCode, code, '', { ...filters, q: localQuery });
  };

  const handleCityChange = (e: SelectChangeEvent<string>) => {
    const name = e.target.value;
    setSelectedCityName(name);
    emitLocationChange(selectedCountryCode, selectedStateCode, name, {
      ...filters,
      q: localQuery,
    });
  };

  const emitDebounced = useCallback(
    (q: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onFiltersChange({ ...filters, q });
      }, DEBOUNCE_MS);
    },
    [filters, onFiltersChange],
  );

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalQuery(val);
    emitDebounced(val);
  };

  const handleMultiSelect = (
    field: 'stages' | 'types' | 'markets',
  ) => (event: any) => {
    const value = event.target.value;
    onFiltersChange({
      ...filters,
      [field]: typeof value === 'string' ? value.split(',') : value,
    });
  };

  const hasAnyFilter =
    filters.q ||
    selectedCountryCode ||
    filters.stages.length > 0 ||
    filters.types.length > 0 ||
    filters.markets.length > 0;

  const handleClearAll = () => {
    setLocalQuery('');
    setSelectedCountryCode('');
    setSelectedStateCode('');
    setSelectedCityName('');
    onFiltersChange({
      q: '',
      location: [],
      stages: [],
      types: [],
      markets: [],
    });
  };

  // Hidden text search for keyboard input (focused from header Search button)
  const searchRef = useRef<HTMLInputElement>(null);

  return (
    <Box>
      {/* Hidden text search field */}
      <TextField
        inputRef={searchRef}
        placeholder="Search by name or company..."
        size="small"
        value={localQuery}
        onChange={handleQueryChange}
        sx={{
          width: '100%',
          mb: 1.5,
          '& .MuiOutlinedInput-root': {
            bgcolor: '#ffffff',
            borderRadius: '8px',
            '& fieldset': { borderColor: '#d1d5db' },
            '&:hover fieldset': { borderColor: '#9ca3af' },
          },
          '& .MuiInputBase-input': { color: '#374151', fontSize: 14 },
        }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <Search size={18} color="#9ca3af" />
              </InputAdornment>
            ),
          },
        }}
      />

      {/* Filter pills row */}
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 1,
          alignItems: 'center',
        }}
      >
        {filtersLoading ? (
          <CircularProgress size={20} sx={{ color: '#4f7df9' }} />
        ) : (
          <>
            {/* Investor Type (types) */}
            <FormControl size="small">
              <Select
                multiple
                displayEmpty
                value={filters.types}
                onChange={handleMultiSelect('types')}
                input={<OutlinedInput />}
                renderValue={(selected) => {
                  const sel = selected as string[];
                  return (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      <Users size={14} color="#6b7280" />
                      <span>{sel.length > 0 ? `Investor Type (${sel.length})` : 'Investor Type'}</span>
                    </Box>
                  );
                }}
                sx={pillSelectSx}
                MenuProps={menuPropsSx}
              >
                {(filterOptions?.types ?? []).map((t) => (
                  <MenuItem key={t} value={t}>
                    <Checkbox checked={filters.types.includes(t)} size="small" sx={{ color: '#4f7df9' }} />
                    <Typography sx={{ color: '#374151', fontSize: 14 }}>{t}</Typography>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Investment Focus (markets) */}
            <FormControl size="small">
              <Select
                multiple
                displayEmpty
                value={filters.markets}
                onChange={handleMultiSelect('markets')}
                input={<OutlinedInput />}
                renderValue={(selected) => {
                  const sel = selected as string[];
                  return (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      <Target size={14} color="#6b7280" />
                      <span>{sel.length > 0 ? `Investment Focus (${sel.length})` : 'Investment Focus'}</span>
                    </Box>
                  );
                }}
                sx={pillSelectSx}
                MenuProps={menuPropsSx}
              >
                {(filterOptions?.markets ?? []).map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    <Checkbox checked={filters.markets.includes(m.id)} size="small" sx={{ color: '#66bb6a' }} />
                    <Typography sx={{ color: '#374151', fontSize: 14 }}>{m.title}</Typography>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Investment Stage */}
            <FormControl size="small">
              <Select
                multiple
                displayEmpty
                value={filters.stages}
                onChange={handleMultiSelect('stages')}
                input={<OutlinedInput />}
                renderValue={(selected) => {
                  const sel = selected as string[];
                  return (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      <TrendingUp size={14} color="#6b7280" />
                      <span>{sel.length > 0 ? `Investment Stage (${sel.length})` : 'Investment Stage'}</span>
                    </Box>
                  );
                }}
                sx={pillSelectSx}
                MenuProps={menuPropsSx}
              >
                {(filterOptions?.stages ?? []).map((s) => (
                  <MenuItem key={s} value={s}>
                    <Checkbox checked={filters.stages.includes(s)} size="small" sx={{ color: '#4f7df9' }} />
                    <Typography sx={{ color: '#374151', fontSize: 14 }}>{s}</Typography>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Country */}
            <FormControl size="small">
              <Select
                value={selectedCountryCode}
                onChange={handleCountryChange}
                displayEmpty
                input={<OutlinedInput />}
                renderValue={() => (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <Globe size={14} color="#6b7280" />
                    <span>
                      {selectedCountryCode
                        ? Country.getCountryByCode(selectedCountryCode)?.name ?? 'Country'
                        : 'Country'}
                    </span>
                  </Box>
                )}
                sx={pillSelectSx}
                MenuProps={menuPropsSx}
              >
                <MenuItem value="">
                  <Typography sx={{ color: '#9ca3af', fontSize: 14 }}>All countries</Typography>
                </MenuItem>
                {ALL_COUNTRIES.map((c) => (
                  <MenuItem key={c.isoCode} value={c.isoCode}>
                    <Typography sx={{ color: '#374151', fontSize: 14 }}>
                      {c.flag} {c.name}
                    </Typography>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* City */}
            <FormControl size="small" disabled={!selectedCountryCode}>
              <Select
                value={selectedCityName}
                onChange={handleCityChange}
                displayEmpty
                input={<OutlinedInput />}
                renderValue={() => (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <MapPin size={14} color="#6b7280" />
                    <span>{selectedCityName || 'City'}</span>
                  </Box>
                )}
                sx={pillSelectSx}
                MenuProps={menuPropsSx}
              >
                <MenuItem value="">
                  <Typography sx={{ color: '#9ca3af', fontSize: 14 }}>All cities</Typography>
                </MenuItem>
                {cityOptions.map((city) => (
                  <MenuItem key={`${city.name}-${city.stateCode}`} value={city.name}>
                    <Typography sx={{ color: '#374151', fontSize: 14 }}>{city.name}</Typography>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* State Name */}
            <FormControl size="small" disabled={!selectedCountryCode}>
              <Select
                value={selectedStateCode}
                onChange={handleStateChange}
                displayEmpty
                input={<OutlinedInput />}
                renderValue={() => (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <Map size={14} color="#6b7280" />
                    <span>
                      {selectedStateCode && selectedCountryCode
                        ? State.getStateByCodeAndCountry(selectedStateCode, selectedCountryCode)?.name ?? 'State Name'
                        : 'State Name'}
                    </span>
                  </Box>
                )}
                sx={pillSelectSx}
                MenuProps={menuPropsSx}
              >
                <MenuItem value="">
                  <Typography sx={{ color: '#9ca3af', fontSize: 14 }}>All states</Typography>
                </MenuItem>
                {stateOptions.map((s) => (
                  <MenuItem key={s.isoCode} value={s.isoCode}>
                    <Typography sx={{ color: '#374151', fontSize: 14 }}>{s.name}</Typography>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </>
        )}

        {hasAnyFilter && (
          <Button
            size="small"
            variant="text"
            onClick={handleClearAll}
            startIcon={<X size={14} />}
            sx={{
              color: '#6b7280',
              textTransform: 'none',
              '&:hover': { color: '#374151' },
            }}
          >
            Clear all
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default InvestorSearchBar;
