# Root layout
`apps/web/app/layout.tsx`
```tsx
import "./styles.css";
export const metadata = { title: "VERITAS · Proof of Reality", description: "Evidence-first document verification" };
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html> }

```
Navigation, sidebar and footer are inline in the two page files; no shared layout component exists.
