type BrandLogoProps={variant?:"light"|"dark"|"auto";markOnly?:boolean;className?:string;decorative?:boolean};

/** Original supplied JPG artwork. The SVG viewport trims only the surrounding margin. */
export default function BrandLogo({variant="auto",markOnly=false,className="",decorative=false}:BrandLogoProps){
 const width=markOnly?178:552,height=208;
 return <svg className={`brand-logo brand-logo--${variant} ${markOnly?"brand-logo--mark":"brand-logo--full"} ${className}`} viewBox={`0 0 ${width} ${height}`} width={width} height={height} role={decorative?undefined:"img"} aria-label={decorative?undefined:"VERITAS"} aria-hidden={decorative||undefined} focusable="false">{(variant==="auto"?["light","dark"]:[variant]).map(tone=><svg key={tone} className={`brand-art brand-art--${tone}`} viewBox={`145 ${tone==="dark"?62:54} ${width} ${tone==="dark"?198:208}`} width={width} height={height} aria-hidden="true"><image href={`/brand/veritas-${tone}.jpg`} x="0" y="0" width="778" height={tone==="dark"?302:321}/></svg>)}</svg>;
}
