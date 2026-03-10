import { useQuery } from '@tanstack/react-query';
import { crmApi, type KanbanShortlist } from '../api/crmApi';
import type { PipelineStage } from '@crm/types/pipeline_stage.types';
import type { Shortlist } from '@crm/types/shortlist.types';
import type { Tag } from '@crm/types/tag.types';
import { fetchInvestorById, fetchInvestorEmails } from '../../investor/api/investorSearchApi';

function calculateDaysInStage(updatedAt: string): number {
  const updated = new Date(updatedAt);
  const now = new Date();
  const diffMs = now.getTime() - updated.getTime();
  return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
}

/**
 * Fetches the current user's shortlists enriched with stage metadata,
 * investor details, tags, and last activity info for Kanban rendering.
 */
export function useUserShortlists(stages: PipelineStage[], tags: Tag[]) {
  return useQuery<KanbanShortlist[]>({
    queryKey: ['crm', 'user-shortlists', stages.length, tags.length],
    queryFn: async () => {
      const shortlists = await crmApi.getShortlists();

      const stageMap = new Map(stages.map((s) => [s.id, s]));
      const tagMap = new Map(tags.map((t) => [t.id, t]));

      // Fetch investor details, activities, and tags for all shortlists in parallel
      const [investorDetails, investorEmails, activitiesPerShortlist, tagsPerShortlist] = await Promise.all([
        Promise.all(
          shortlists.map((sl) =>
            fetchInvestorById(sl.investor_id).catch(() => null),
          ),
        ),
        Promise.all(
          shortlists.map((sl) =>
            fetchInvestorEmails(sl.investor_id).catch(() => []),
          ),
        ),
        Promise.all(
          shortlists.map((sl) =>
            crmApi.getActivities(sl.id).catch(() => []),
          ),
        ),
        Promise.all(
          shortlists.map((sl) =>
            crmApi.getShortlistTags(sl.id).catch(() => []),
          ),
        ),
      ]);

      return shortlists.map((sl: Shortlist, idx: number): KanbanShortlist => {
        const stage = sl.stage_id ? stageMap.get(sl.stage_id) : undefined;
        const investor = investorDetails[idx];
        const emails = investorEmails[idx] || [];
        const activities = activitiesPerShortlist[idx] || [];
        const shortlistTags = tagsPerShortlist[idx] || [];
        const lastActivity = activities[0]; // already sorted desc by date

        const resolvedTags = shortlistTags
          .map((st) => {
            const tag = tagMap.get(st.tag_id);
            if (!tag) return null;
            return { id: tag.id, name: tag.name, color: tag.color };
          })
          .filter(Boolean) as Array<{ id: string; name: string; color: string | null }>;

        // Build location from investor data
        const locationParts = [investor?.city, investor?.state, investor?.country].filter(Boolean);
        const location = locationParts.join(', ');

        return {
          ...sl,
          stage_name: stage?.name,
          stage_color: stage?.color || '#3B82F6',
          stage_sequence: stage?.sequence ?? 999,
          investor_name: investor?.name || undefined,
          investor_company: investor?.company_name || undefined,
          investor_location: location || undefined,
          investor_email: emails[0]?.email || undefined,
          last_activity_summary: lastActivity?.summary || undefined,
          last_activity_date: lastActivity?.date || undefined,
          tags: resolvedTags,
          days_in_stage: calculateDaysInStage(sl.updated_at),
        };
      });
    },
    enabled: stages.length > 0,
    staleTime: 2 * 60 * 1000,
  });
}
