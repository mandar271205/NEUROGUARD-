import { AppShell } from "@/components/app-shell";
import { StudentDetail } from "@/components/student-detail";

export default async function StudentDetailPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <AppShell>
      <StudentDetail studentId={id} />
    </AppShell>
  );
}
