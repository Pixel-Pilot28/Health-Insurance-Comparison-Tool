/**
 * OPM Parser Reconciliation UI Component
 * 
 * Features:
 * - View parse report with ambiguous cells
 * - Edit parsed benefit fields (copay, coinsurance, cap, flags)
 * - Accept/reject column mapping suggestions
 * - Save overrides to backend
 * - Trigger parser reruns
 * - View parsing statistics
 */

import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  IconButton,
  Paper,
  Switch,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Snackbar,
  Tooltip,
  Divider
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  Download as DownloadIcon,
  PlayArrow as PlayArrowIcon
} from '@mui/icons-material';

// Types
interface AmbiguousCell {
  plan: string;
  enrollment_code: string;
  column: string;
  raw: string;
  parsed?: {
    copay?: number;
    coinsurance?: number;
    cap?: number;
    min_value?: number;
    max_value?: number;
    applies_after_deductible?: boolean;
    prior_authorization?: boolean;
    network_only?: boolean;
    first_visit_only?: boolean;
  };
}

interface ParseReport {
  ambiguous_cells: AmbiguousCell[];
  unmapped_columns: string[];
  column_suggestions: Record<string, [string, number][]>;
  total_plans: number;
  total_columns: number;
  timestamp: string;
}

interface Overrides {
  version: string;
  last_updated?: string;
  description?: string;
  column_map: Record<string, string>;
  plan_overrides: Record<string, Record<string, any>>;
  ignore_columns?: string[];
}

interface ParserStats {
  total_plans: number;
  total_columns: number;
  ambiguous_cells_count: number;
  unmapped_columns_count: number;
  timestamp: string;
  overrides_active: boolean;
}

// Main Component
export default function OpmReconcile() {
  const [activeTab, setActiveTab] = useState(0);
  const [report, setReport] = useState<ParseReport | null>(null);
  const [overrides, setOverrides] = useState<Overrides | null>(null);
  const [stats, setStats] = useState<ParserStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedCell, setSelectedCell] = useState<AmbiguousCell | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });
  const [parserRunning, setParserRunning] = useState(false);

  // Fetch data on mount
  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchReport(),
        fetchOverrides(),
        fetchStats()
      ]);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReport = async () => {
    try {
      const res = await fetch('/api/opm/parse-report');
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (error) {
      console.error('Error fetching parse report:', error);
    }
  };

  const fetchOverrides = async () => {
    try {
      const res = await fetch('/api/opm/overrides');
      if (res.ok) {
        const data = await res.json();
        setOverrides(data);
      }
    } catch (error) {
      console.error('Error fetching overrides:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/opm/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleSaveOverride = async (planKey: string, updates: Record<string, any>) => {
    try {
      const res = await fetch('/api/opm/overrides', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...overrides,
          plan_overrides: {
            ...overrides?.plan_overrides,
            [planKey]: {
              ...(overrides?.plan_overrides?.[planKey] || {}),
              ...updates
            }
          }
        })
      });

      if (res.ok) {
        setSnackbar({ open: true, message: 'Override saved successfully!', severity: 'success' });
        await fetchOverrides();
        setEditDialogOpen(false);
      } else {
        throw new Error('Failed to save override');
      }
    } catch (error) {
      console.error('Error saving override:', error);
      setSnackbar({ open: true, message: 'Failed to save override', severity: 'error' });
    }
  };

  const handleAcceptSuggestion = async (opmColumn: string, canonicalTarget: string) => {
    try {
      const res = await fetch('/api/opm/accept-suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          opm_column: opmColumn,
          canonical_target: canonicalTarget
        })
      });

      if (res.ok) {
        setSnackbar({ open: true, message: `Mapping accepted: ${opmColumn} → ${canonicalTarget}`, severity: 'success' });
        await fetchOverrides();
      } else {
        throw new Error('Failed to accept suggestion');
      }
    } catch (error) {
      console.error('Error accepting suggestion:', error);
      setSnackbar({ open: true, message: 'Failed to accept suggestion', severity: 'error' });
    }
  };

  const handleRunParser = async () => {
    setParserRunning(true);
    try {
      const res = await fetch('/api/opm/run-parser', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          use_fuzzy: true,
          min_score: 0.6
        })
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setSnackbar({ open: true, message: 'Parser completed successfully!', severity: 'success' });
        await fetchAll();
      } else {
        throw new Error(data.message || 'Parser execution failed');
      }
    } catch (error: any) {
      console.error('Error running parser:', error);
      setSnackbar({ open: true, message: error.message || 'Failed to run parser', severity: 'error' });
    } finally {
      setParserRunning(false);
    }
  };

  const handleDownloadCSV = () => {
    window.open('/api/opm/parsed-csv', '_blank');
  };

  if (loading && !report) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          OPM Parser Reconciliation
        </Typography>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchAll}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleDownloadCSV}
          >
            Download CSV
          </Button>
          <Button
            variant="contained"
            startIcon={parserRunning ? <CircularProgress size={20} /> : <PlayArrowIcon />}
            onClick={handleRunParser}
            disabled={parserRunning}
          >
            {parserRunning ? 'Running...' : 'Run Parser'}
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      {stats && (
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Plans
                </Typography>
                <Typography variant="h4">{stats.total_plans}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Ambiguous Cells
                </Typography>
                <Typography variant="h4" color={stats.ambiguous_cells_count > 0 ? 'error' : 'success'}>
                  {stats.ambiguous_cells_count}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Unmapped Columns
                </Typography>
                <Typography variant="h4" color={stats.unmapped_columns_count > 0 ? 'warning.main' : 'success'}>
                  {stats.unmapped_columns_count}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Overrides Active
                </Typography>
                <Typography variant="h4">
                  {stats.overrides_active ? (
                    <CheckIcon color="success" />
                  ) : (
                    <CloseIcon color="disabled" />
                  )}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
          <Tab label={`Ambiguous Cells (${report?.ambiguous_cells?.length || 0})`} />
          <Tab label={`Unmapped Columns (${report?.unmapped_columns?.length || 0})`} />
          <Tab label="Overrides" />
          <Tab label="Statistics" />
        </Tabs>
      </Paper>

      {/* Tab Panels */}
      {activeTab === 0 && <AmbiguousCellsPanel report={report} onEdit={(cell) => { setSelectedCell(cell); setEditDialogOpen(true); }} />}
      {activeTab === 1 && <UnmappedColumnsPanel report={report} onAcceptSuggestion={handleAcceptSuggestion} />}
      {activeTab === 2 && <OverridesPanel overrides={overrides} />}
      {activeTab === 3 && <StatisticsPanel report={report} stats={stats} />}

      {/* Edit Dialog */}
      <EditCellDialog
        open={editDialogOpen}
        cell={selectedCell}
        onClose={() => setEditDialogOpen(false)}
        onSave={handleSaveOverride}
      />

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

// Ambiguous Cells Panel
function AmbiguousCellsPanel({ report, onEdit }: { report: ParseReport | null; onEdit: (cell: AmbiguousCell) => void }) {
  if (!report || report.ambiguous_cells.length === 0) {
    return (
      <Box p={3}>
        <Alert severity="success">
          No ambiguous cells! All benefit strings were parsed successfully.
        </Alert>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Plan</TableCell>
            <TableCell>Enrollment Code</TableCell>
            <TableCell>Column</TableCell>
            <TableCell>Raw Value</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {report.ambiguous_cells.map((cell, idx) => (
            <TableRow key={idx} hover>
              <TableCell>{cell.plan}</TableCell>
              <TableCell>{cell.enrollment_code}</TableCell>
              <TableCell>{cell.column}</TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                  {cell.raw}
                </Typography>
              </TableCell>
              <TableCell align="center">
                <Tooltip title="Edit parsed values">
                  <IconButton size="small" color="primary" onClick={() => onEdit(cell)}>
                    <EditIcon />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

// Unmapped Columns Panel
function UnmappedColumnsPanel({ 
  report, 
  onAcceptSuggestion 
}: { 
  report: ParseReport | null; 
  onAcceptSuggestion: (opm: string, target: string) => void 
}) {
  if (!report || report.unmapped_columns.length === 0) {
    return (
      <Box p={3}>
        <Alert severity="success">
          All columns were successfully mapped!
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Alert severity="warning" sx={{ mb: 3 }}>
        The following columns could not be automatically mapped. Review the suggestions and accept the best match.
      </Alert>

      <Grid container spacing={3}>
        {report.unmapped_columns.map((column, idx) => {
          const suggestions = report.column_suggestions?.[column] || [];
          return (
            <Grid item xs={12} key={idx}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {column}
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  {suggestions.length > 0 ? (
                    <Box>
                      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                        Suggestions (click to accept):
                      </Typography>
                      <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
                        {suggestions.map(([target, score], sidx) => (
                          <Chip
                            key={sidx}
                            label={`${target} (${(score * 100).toFixed(0)}%)`}
                            color={score > 0.7 ? 'primary' : 'default'}
                            onClick={() => onAcceptSuggestion(column, target)}
                            clickable
                          />
                        ))}
                      </Box>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="textSecondary">
                      No suggestions available. Consider adding a manual mapping in overrides.json.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}

// Overrides Panel
function OverridesPanel({ overrides }: { overrides: Overrides | null }) {
  if (!overrides) {
    return (
      <Box p={3}>
        <CircularProgress />
      </Box>
    );
  }

  const columnMapCount = Object.keys(overrides.column_map || {}).length;
  const planOverrideCount = Object.keys(overrides.plan_overrides || {}).length;

  return (
    <Box p={3}>
      <Grid container spacing={3}>
        {/* Column Mappings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Column Mappings ({columnMapCount})
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {columnMapCount > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>OPM Column</TableCell>
                        <TableCell>→</TableCell>
                        <TableCell>Canonical Field</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(overrides.column_map).map(([opm, canonical], idx) => (
                        <TableRow key={idx}>
                          <TableCell>{opm}</TableCell>
                          <TableCell>→</TableCell>
                          <TableCell><strong>{canonical}</strong></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" color="textSecondary">
                  No column mappings configured yet.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Plan Overrides */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Plan Overrides ({planOverrideCount})
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {planOverrideCount > 0 ? (
                <Box>
                  {Object.entries(overrides.plan_overrides).map(([planKey, fields], idx) => (
                    <Box key={idx} mb={2}>
                      <Typography variant="subtitle2" color="primary">
                        {planKey}
                      </Typography>
                      <Box ml={2}>
                        {Object.entries(fields)
                          .filter(([key]) => !key.startsWith('_'))
                          .map(([field, value], fidx) => (
                            <Typography key={fidx} variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                              {field}: {JSON.stringify(value)}
                            </Typography>
                          ))}
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="textSecondary">
                  No plan-specific overrides configured yet.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Metadata */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Metadata
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="body2">
                <strong>Version:</strong> {overrides.version}
              </Typography>
              {overrides.last_updated && (
                <Typography variant="body2">
                  <strong>Last Updated:</strong> {new Date(overrides.last_updated).toLocaleString()}
                </Typography>
              )}
              {overrides.description && (
                <Typography variant="body2">
                  <strong>Description:</strong> {overrides.description}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

// Statistics Panel
function StatisticsPanel({ report, stats }: { report: ParseReport | null; stats: ParserStats | null }) {
  if (!report || !stats) {
    return (
      <Box p={3}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Parse Summary
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Box display="flex" flexDirection="column" gap={1}>
                <Box display="flex" justifyContent="space-between">
                  <Typography>Total Plans:</Typography>
                  <Typography><strong>{stats.total_plans}</strong></Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography>Total Columns:</Typography>
                  <Typography><strong>{stats.total_columns}</strong></Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography>Ambiguous Cells:</Typography>
                  <Typography color={stats.ambiguous_cells_count > 0 ? 'error' : 'success'}>
                    <strong>{stats.ambiguous_cells_count}</strong>
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography>Unmapped Columns:</Typography>
                  <Typography color={stats.unmapped_columns_count > 0 ? 'warning.main' : 'success'}>
                    <strong>{stats.unmapped_columns_count}</strong>
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography>Parse Time:</Typography>
                  <Typography><strong>{new Date(stats.timestamp).toLocaleString()}</strong></Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Parsing Quality
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Box display="flex" flexDirection="column" gap={2}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Success Rate
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Box sx={{ width: '100%', bgcolor: 'grey.200', borderRadius: 1, height: 24 }}>
                      <Box
                        sx={{
                          width: `${((stats.total_plans * stats.total_columns - stats.ambiguous_cells_count) / (stats.total_plans * stats.total_columns) * 100).toFixed(1)}%`,
                          bgcolor: 'success.main',
                          height: '100%',
                          borderRadius: 1,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        <Typography variant="caption" sx={{ color: 'white', fontWeight: 'bold' }}>
                          {((stats.total_plans * stats.total_columns - stats.ambiguous_cells_count) / (stats.total_plans * stats.total_columns) * 100).toFixed(1)}%
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                </Box>

                <Box>
                  <Typography variant="body2" gutterBottom>
                    Column Mapping Rate
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Box sx={{ width: '100%', bgcolor: 'grey.200', borderRadius: 1, height: 24 }}>
                      <Box
                        sx={{
                          width: `${((stats.total_columns - stats.unmapped_columns_count) / stats.total_columns * 100).toFixed(1)}%`,
                          bgcolor: 'primary.main',
                          height: '100%',
                          borderRadius: 1,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        <Typography variant="caption" sx={{ color: 'white', fontWeight: 'bold' }}>
                          {((stats.total_columns - stats.unmapped_columns_count) / stats.total_columns * 100).toFixed(1)}%
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

// Edit Cell Dialog
function EditCellDialog({ 
  open, 
  cell, 
  onClose, 
  onSave 
}: { 
  open: boolean; 
  cell: AmbiguousCell | null; 
  onClose: () => void; 
  onSave: (planKey: string, updates: Record<string, any>) => void 
}) {
  const [copay, setCopay] = useState('');
  const [coinsurance, setCoinsurance] = useState('');
  const [cap, setCap] = useState('');
  const [minValue, setMinValue] = useState('');
  const [maxValue, setMaxValue] = useState('');
  const [afterDeductible, setAfterDeductible] = useState(false);
  const [priorAuth, setPriorAuth] = useState(false);
  const [networkOnly, setNetworkOnly] = useState(false);

  useEffect(() => {
    if (cell) {
      // Reset fields when cell changes
      setCopay('');
      setCoinsurance('');
      setCap('');
      setMinValue('');
      setMaxValue('');
      setAfterDeductible(false);
      setPriorAuth(false);
      setNetworkOnly(false);
    }
  }, [cell]);

  const handleSave = () => {
    if (!cell) return;

    const planKey = `EnrollmentCode_${cell.enrollment_code}`;
    const columnPrefix = cell.column.replace(/ /g, '_');
    
    const updates: Record<string, any> = {
      [`${columnPrefix}_raw`]: cell.raw
    };

    if (copay) updates[`${columnPrefix}_money`] = parseFloat(copay);
    if (coinsurance) updates[`${columnPrefix}_percent`] = parseFloat(coinsurance);
    if (cap) updates[`${columnPrefix}_cap`] = parseFloat(cap);
    if (minValue) updates[`${columnPrefix}_min_value`] = parseFloat(minValue);
    if (maxValue) updates[`${columnPrefix}_max_value`] = parseFloat(maxValue);
    if (afterDeductible) updates[`${columnPrefix}_applies_after_deductible`] = true;
    if (priorAuth) updates[`${columnPrefix}_prior_authorization`] = true;
    if (networkOnly) updates[`${columnPrefix}_network_only`] = true;

    updates[`_note`] = `Manual override for ${cell.column}`;

    onSave(planKey, updates);
  };

  if (!cell) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Edit: {cell.column}
        <Typography variant="caption" display="block" color="textSecondary">
          {cell.plan} (Code: {cell.enrollment_code})
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Box mb={2} p={2} bgcolor="grey.100" borderRadius={1}>
          <Typography variant="subtitle2" gutterBottom>
            Raw Value:
          </Typography>
          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
            {cell.raw}
          </Typography>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Copay ($)"
              type="number"
              value={copay}
              onChange={(e) => setCopay(e.target.value)}
              helperText="Fixed dollar amount"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Coinsurance (%)"
              type="number"
              value={coinsurance}
              onChange={(e) => setCoinsurance(e.target.value)}
              helperText="Percentage (e.g., 20 for 20%)"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Cap/Max ($)"
              type="number"
              value={cap}
              onChange={(e) => setCap(e.target.value)}
              helperText="Maximum out-of-pocket"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Min Value ($)"
              type="number"
              value={minValue}
              onChange={(e) => setMinValue(e.target.value)}
              helperText="For ranges: minimum"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Max Value ($)"
              type="number"
              value={maxValue}
              onChange={(e) => setMaxValue(e.target.value)}
              helperText="For ranges: maximum"
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle2" gutterBottom>
          Flags
        </Typography>
        <Grid container spacing={1}>
          <Grid item xs={12} sm={4}>
            <FormControlLabel
              control={<Switch checked={afterDeductible} onChange={(e) => setAfterDeductible(e.target.checked)} />}
              label="After Deductible"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControlLabel
              control={<Switch checked={priorAuth} onChange={(e) => setPriorAuth(e.target.checked)} />}
              label="Prior Auth Required"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <FormControlLabel
              control={<Switch checked={networkOnly} onChange={(e) => setNetworkOnly(e.target.checked)} />}
              label="Network Only"
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          Save Override
        </Button>
      </DialogActions>
    </Dialog>
  );
}
